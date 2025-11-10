import os
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage

load_dotenv()
PRIVATE_MODE = os.getenv('PRIVATE_MODE', 'false').lower() == 'true'
USE_REAL_LLM_IN_PRIVATE_MODE = os.getenv('USE_REAL_LLM_IN_PRIVATE_MODE', 'false').lower() == 'true'

class DummyLocalLLM(BaseChatModel):
    """LLM de respaldo para modo privado o cuando no hay configuración de modelo real.
    Genera respuestas simples y deterministas para permitir que la app funcione offline."""
    def __init__(self, agent: str):
        super().__init__()
        self.agent = agent

    def _strip(self, text: str) -> str:
        return ' '.join(text.strip().split())

    def _classify(self, user_text: str):
        t = user_text.lower()
        desktop_verbs = ['open', 'abrir', 'launch', 'inicia', 'iniciar', 'click', 'clic', 'type', 'escribe', 'send', 'enviar', 'navigate', 'navega', 'buscar', 'search']
        is_desktop = any(v in t for v in desktop_verbs)
        return {
            "type": "desktop_task" if is_desktop else "inquiry",
            "response": "Entendido, comenzaré." if is_desktop else "Respuesta: " + user_text[:120],
            "is_browser_task": any(w in t for w in ['web', 'browser', 'navega', 'http', 'https']),
            "needs_memory_from_previous_tasks": any(w in t for w in ['otra vez', 'again', 'igual', 'mismo', 'previous']),
            "is_background_mode_requested": any(w in t for w in ['background', 'segundo plano']),
            "is_extended_thinking_mode_requested": any(w in t for w in ['think more', 'pensar más', 'full analysis']),
        }

    def _title(self, user_text: str):
        clean = self._strip(user_text)
        words = clean.split()
        short = ' '.join(words[:8])
        return {"title": short.title() or "Task"}

    def _planner(self, goal: str):
        # Extra simple: devuelve un único subtask con el goal
        return {"subtasks": [{"subtask": self._strip(goal)[:160], "type": "desktop_subtask"}]}

    def _suggestor(self):
        return {"suggestions": []}

    def _computer_use(self):
        # Devuelve un JSON válido con finalización inmediata del subtask
        return {
            "current_state": {
                "evaluation_previous_goal": "Unknown",
                "memory": "(dummy) no-op",
                "save_to_memory": False,
                "next_goal": ""
            },
            "actions": [ { "action": "subtask_completed", "params": {} } ]
        }

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        # El último mensaje del usuario suele estar al final
        user_text = ''
        if messages:
            # Filtrar mensajes con .content
            for m in reversed(messages):
                if hasattr(m, 'content') and isinstance(m.content, str):
                    user_text = m.content
                    break
        if self.agent == 'classifier':
            payload = self._classify(user_text)
        elif self.agent == 'title':
            payload = self._title(user_text)
        elif self.agent == 'planner':
            payload = self._planner(user_text)
        elif self.agent == 'suggestor':
            payload = self._suggestor()
        elif self.agent == 'computer_use':
            payload = self._computer_use()
        else:
            payload = {"message": "Dummy response", "agent": self.agent}
        content = json_dumps(payload)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @property
    def _llm_type(self) -> str:
        return "dummy_local_llm"


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def _has_provider_credentials(model_type: str) -> bool:
    if model_type == 'openai':
        return bool(os.getenv('OPENAI_API_KEY'))
    if model_type == 'azure_openai':
        return bool(os.getenv('AZURE_OPENAI_API_KEY') and os.getenv('AZURE_OPENAI_ENDPOINT'))
    if model_type == 'anthropic':
        return bool(os.getenv('ANTHROPIC_API_KEY'))
    if model_type == 'bedrock':
        return bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
    return False


def get_llm(agent: str, temperature: float = 0.0, max_tokens: int = None, thinking_enabled: bool = False) -> BaseChatModel:
    model_type = os.getenv(f"{agent.upper()}_AGENT_MODEL_TYPE")
    model_id = os.getenv(f"{agent.upper()}_AGENT_MODEL_ID")
    # Fallback si no hay config; pero si PRIVATE_MODE y se ha solicitado uso real, no forzar dummy.
    if (not model_type or not model_id) or (PRIVATE_MODE and not USE_REAL_LLM_IN_PRIVATE_MODE) or (model_type and not _has_provider_credentials(model_type)):
        return DummyLocalLLM(agent=agent)
    try:
        if model_type == 'openai':
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_id, temperature=temperature, max_tokens=max_tokens, timeout=None, max_retries=2, openai_api_key=os.getenv('OPENAI_API_KEY'))
        elif model_type == 'azure_openai':
            from langchain_openai import AzureChatOpenAI
            return AzureChatOpenAI(azure_deployment=model_id, api_version=os.getenv('OPENAI_API_VERSION', '2024-12-01-preview'), temperature=temperature, max_tokens=max_tokens, timeout=None, max_retries=2)
        elif model_type == 'anthropic':
            from langchain_anthropic import ChatAnthropic
            if not thinking_enabled:
                return ChatAnthropic(model=model_id, anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'), temperature=temperature, max_tokens=max_tokens)
            else:
                return ChatAnthropic(model=model_id, anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'), temperature=temperature, max_tokens=max_tokens, thinking={"type": "enabled", "budget_tokens": 2000})
        elif model_type == 'bedrock':
            from botocore.config import Config
            from langchain_aws import ChatBedrockConverse
            boto3_config = Config(connect_timeout=300, read_timeout=300, retries={'max_attempts': 5}, region_name=os.getenv('BEDROCK_REGION', 'us-east-1'))
            if thinking_enabled and 'claude' in model_id:
                return ChatBedrockConverse(model=model_id, temperature=temperature, max_tokens=max_tokens, config=boto3_config, region_name=os.getenv('BEDROCK_REGION', 'us-east-1'), additional_model_request_fields={"thinking": {"type": "enabled", "budget_tokens": 2000}})
            else:
                return ChatBedrockConverse(model=model_id, temperature=temperature, max_tokens=max_tokens, config=boto3_config, region_name=os.getenv('BEDROCK_REGION', 'us-east-1'))
        else:
            return DummyLocalLLM(agent=agent)
    except ImportError:
        return DummyLocalLLM(agent=agent)
    except Exception:
        return DummyLocalLLM(agent=agent)
