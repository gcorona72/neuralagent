import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.apps.auth import router as userauth_router
from routers.aiagent.generic import router as aiagent_router
from routers.apps.threads import router as threads_router
from routers.aiagent.suggestor import router as suggestor_aiagent_router
from routers.aiagent.background import router as bg_mode_aiagent_router
from routers.apps.voice import router as voice_router
from utils.procedures import CustomError
from fastapi.staticfiles import StaticFiles
import os

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title='NeuralAgent'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        '*',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(CustomError)
async def custom_http_exception_handler(request: Request, exc: CustomError):
    return JSONResponse(
        status_code=exc.status_code,
        content={'message': exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    print('[ERROR] Unhandled exception:', tb)
    return JSONResponse(status_code=500, content={"error": str(exc)})


app.include_router(userauth_router)
app.include_router(threads_router)
app.include_router(suggestor_aiagent_router)
app.include_router(bg_mode_aiagent_router)
app.include_router(aiagent_router)
app.include_router(voice_router)

# Montar archivos estáticos locales para modo privado
LOCAL_STORAGE_DIR = os.getenv('LOCAL_STORAGE_DIR') or os.path.join(os.path.dirname(__file__), 'local_storage')
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
app.mount('/static/files', StaticFiles(directory=LOCAL_STORAGE_DIR), name='local_files')

# Crear tablas si no existen (útil en modo local/SQLite)
from sqlmodel import SQLModel
from db.database import engine
# Importa modelos para registrar tablas en el metadata
from db import models as _models  # noqa: F401

@app.on_event('startup')
def _ensure_db_tables():
    try:
        SQLModel.metadata.create_all(bind=engine)
    except Exception as e:
        print('[startup] DB init error:', e)


@app.get('/')
async def index():
    return {'message': datetime.datetime.now()}

from fastapi import APIRouter
from utils.upload_helper import list_files, open_file, delete_file

# Crear un router para manejar archivos adjuntos
attachments_router = APIRouter()

@attachments_router.get("/attachments")
async def list_attachments():
    return {"files": list_files()}

@attachments_router.get("/attachments/{filename}")
async def download_attachment(filename: str):
    return open_file(filename)

@attachments_router.delete("/attachments/{filename}")
async def remove_attachment(filename: str):
    delete_file(filename)
    return {"message": "Archivo eliminado exitosamente"}

# Incluir el router en la aplicación principal
app.include_router(attachments_router)
