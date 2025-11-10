from .aws_s3 import get_s3_client, generate_signed_url
from fastapi import HTTPException
import os
from .procedures import generate_random_string
try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None  # PIL opcional
import io
from fastapi.responses import FileResponse
from PyPDF2 import PdfReader
import pytesseract

# --- Almacenamiento local (modo privado) ---
BASE_LOCAL_DIR = os.getenv('LOCAL_STORAGE_DIR') or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_storage')
LOCAL_UPLOADS_DIR = os.path.join(BASE_LOCAL_DIR, 'uploads')
LOCAL_SCREENSHOTS_DIR = os.path.join(BASE_LOCAL_DIR, 'screenshots')


def _ensure_dirs():
    os.makedirs(LOCAL_UPLOADS_DIR, exist_ok=True)
    os.makedirs(LOCAL_SCREENSHOTS_DIR, exist_ok=True)


def save_bytes_local(data: bytes, extension: str = '') -> str:
    """Guarda bytes en carpeta local uploads y devuelve ruta relativa dentro de local_storage.
    Retorna, por ejemplo: 'uploads/abc123.png'
    """
    _ensure_dirs()
    ext = extension.lstrip('.') if extension else ''
    new_filename = f"{generate_random_string()}{('.' + ext) if ext else ''}"
    rel_path = os.path.join('uploads', new_filename)
    abs_path = os.path.join(BASE_LOCAL_DIR, rel_path)
    with open(abs_path, 'wb') as f:
        f.write(data)
    return rel_path


def get_local_file_url(rel_path: str) -> str:
    """Construye URL pública relativa expuesta por FastAPI: /static/files/{rel_path}"""
    rel_path = rel_path.replace('\\', '/')
    if rel_path.startswith('/'):
        rel_path = rel_path[1:]
    return f"/static/files/{rel_path}"


# --- S3 helpers existentes ---

def upload_file_s3(file):
    try:
        ext = file.filename.split('.')[-1]
        new_filename = '{}.{}'.format(generate_random_string(), ext)
        filepath = '{}/{}'.format('neuralagent_clients', new_filename)

        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            file.file,
            os.getenv('AWS_BUCKET'),
            filepath
        )

        return filepath
    except Exception as e:
        return None


def upload_screenshot_s3_bytesio(buffer: io.BytesIO, extension="png"):
    try:
        new_filename = f"{generate_random_string()}.{extension}"
        filepath = f"neuralagent_screenshots/{new_filename}"

        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            buffer,
            os.getenv('AWS_BUCKET'),
            filepath
        )

        return filepath
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {e}")


def generate_thumbnail(image_data, size):
    """
        Generate a thumbnail of the given size.

        :param image_data: Binary image data.
        :param size: Tuple (width, height) for the thumbnail.
        :return: BytesIO object containing the resized image.
        """
    if Image is None:
        raise HTTPException(status_code=500, detail='Pillow (PIL) not installed')
    image = Image.open(io.BytesIO(image_data))
    image.thumbnail(size)  # Resize the image while maintaining aspect ratio

    # Save thumbnail to a BytesIO object
    thumb_io = io.BytesIO()
    image.save(thumb_io, format=image.format)
    thumb_io.seek(0)
    return thumb_io


async def upload_image_s3(image):
    image_data = await image.read()
    thumb_sm = generate_thumbnail(image_data, (200, 200))
    thumb_lg = generate_thumbnail(image_data, (700, 700))

    ext = image.filename.split('.')[-1]
    random_string = generate_random_string()

    new_filename = '{}.{}'.format(random_string, ext)
    thumb_sm_name = '{}.thumb_sm.{}'.format(random_string, ext)
    thumb_lg_name = '{}.thumb_lg.{}'.format(random_string, ext)

    filepath = '{}/{}'.format('neuralagent_clients', new_filename)
    thumb_sm_path = '{}/{}'.format('neuralagent_clients', thumb_sm_name)
    thumb_lg_path = '{}/{}'.format('neuralagent_clients', thumb_lg_name)

    s3_client = get_s3_client()
    s3_client.upload_fileobj(
        image.file,
        os.getenv('AWS_BUCKET'),
        filepath
    )

    s3_client.upload_fileobj(
        thumb_sm,
        os.getenv('AWS_BUCKET'),
        thumb_sm_path
    )

    s3_client.upload_fileobj(
        thumb_lg,
        os.getenv('AWS_BUCKET'),
        thumb_lg_path
    )

    return filepath


def get_file_url(filepath):
    return generate_signed_url(filepath, 3600 * 3)


def construct_image_obj(image):
    ext = image.split('.')[-1]
    name = image.split('.')[0]

    image_path = '{}.{}'.format(name, ext)
    thumb_sm_path = '{}.thumb_sm.{}'.format(name, ext)
    thumb_lg_path = '{}.thumb_lg.{}'.format(name, ext)

    return {
        'original': get_file_url(image_path),
        'thumb_sm': get_file_url(thumb_sm_path),
        'thumb_lg': get_file_url(thumb_lg_path)
    }


# Función para listar archivos adjuntos
def list_files() -> list:
    """Lista todos los archivos en la carpeta de uploads."""
    _ensure_dirs()
    return os.listdir(LOCAL_UPLOADS_DIR)


# Función para abrir/descargar un archivo adjunto
def open_file(filename: str) -> FileResponse:
    """Devuelve un archivo como respuesta para descarga."""
    file_path = os.path.join(LOCAL_UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(file_path, filename=filename)


# Función para borrar un archivo adjunto
def delete_file(filename: str):
    """Elimina un archivo de la carpeta de uploads."""
    file_path = os.path.join(LOCAL_UPLOADS_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")


# Función para procesar PDF/DOCX e imágenes con OCR
def process_file(file_path: str) -> str:
    """Procesa un archivo y extrae texto si es PDF, DOCX o imagen."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        reader = PdfReader(file_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''
        return text
    elif ext in ['.jpg', '.jpeg', '.png']:
        if not Image:
            raise HTTPException(status_code=500, detail="Pillow no está instalado para procesar imágenes.")
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)
    else:
        raise HTTPException(status_code=400, detail="Tipo de archivo no soportado para procesamiento.")
