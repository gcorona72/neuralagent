# Optional import for UnstructuredPDFLoader (heavy dependency). Fallback to PyPDF if missing.
try:
    from langchain_community.document_loaders import UnstructuredPDFLoader  # type: ignore
except Exception:  # pragma: no cover
    UnstructuredPDFLoader = None  # type: ignore

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader, YoutubeLoader
from langchain_core.prompts import ChatPromptTemplate
from . import llm_provider


def _get_llm_for_tools():
    # Reutiliza el modelo configurado para el SUGGESTOR por defecto; es barato para resúmenes
    try:
        return llm_provider.get_llm(agent='suggestor', temperature=0.2)
    except Exception:
        # Fallback mínimo si falta config del suggestor: usa planner
        return llm_provider.get_llm(agent='planner', temperature=0.2)


def _summarize_text(full_text: str) -> str:
    llm = _get_llm_for_tools()
    prompt = ChatPromptTemplate.from_template("Summarize the following:")
    chain = prompt | llm
    result = chain.invoke({"input": full_text})
    # Algunos LLMs devuelven .content directamente, otros un objeto
    return getattr(result, 'content', str(result))


def fetch_and_summarize_url(url: str) -> str:
    loader = WebBaseLoader(url)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=120)
    docs = text_splitter.split_documents(documents)

    full_text = "\n\n".join(doc.page_content for doc in docs)
    return _summarize_text(full_text)


def fetch_and_summarize_pdf(file_path: str = None, url: str = None) -> str:
    if url and not file_path:
        import requests
        import tempfile
        response = requests.get(url)
        response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(response.content)
        temp_file.close()
        file_path = temp_file.name

    documents = []
    try:
        if UnstructuredPDFLoader is not None:
            loader = UnstructuredPDFLoader(file_path)
            documents = loader.load()
        else:
            raise RuntimeError('unstructured not installed')
    except Exception:
        # Fallback a PyPDF si Unstructured falla o no existe
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        except Exception as e:
            return f"Failed to read PDF: {e}"

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=120)
    docs = text_splitter.split_documents(documents)

    full_text = "\n\n".join(doc.page_content for doc in docs)
    return _summarize_text(full_text)


def summarize_youtube_video(url: str) -> str:
    try:
        loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
        documents = loader.load()
    except Exception as e:
        return f"Unexpected error fetching video transcript: {str(e)}"

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=120)
    docs = text_splitter.split_documents(documents)

    full_text = "\n\n".join(doc.page_content for doc in docs)
    return _summarize_text(full_text)


def run_tool_server_side(tool_name: str, args: dict) -> str:
    if tool_name == "fetch_url":
        return fetch_and_summarize_url(args["url"]) if args.get("url") else "Missing url"

    if tool_name == "read_pdf":
        return fetch_and_summarize_pdf(args.get("file_path"), args.get("url"))

    if tool_name == "summarize_youtube_video":
        return summarize_youtube_video(args["url"]) if args.get("url") else "Missing url"

    raise ValueError(f"Unsupported tool: {tool_name}")