from fastapi import APIRouter, UploadFile, File, Depends, status
from dependencies.auth_dependencies import get_current_user_dependency
from utils.procedures import CustomError
import os, tempfile
from typing import Optional

router = APIRouter(
    prefix='/apps/voice',
    tags=['apps', 'voice'],
    dependencies=[Depends(get_current_user_dependency)]
)

WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'small')
PRIVATE_MODE = os.getenv('PRIVATE_MODE', 'false').lower() == 'true'

_model_cache = {
    'model': None,
    'name': None,
}

def _load_model(name: str):
    from faster_whisper import WhisperModel
    if _model_cache['model'] is None or _model_cache['name'] != name:
        compute_type = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')  # int8 / float16 / float32
        _model_cache['model'] = WhisperModel(name, device="auto", compute_type=compute_type)
        _model_cache['name'] = name
    return _model_cache['model']

@router.post('/transcribe')
async def transcribe_audio(audio: UploadFile = File(...)):
    # Validar tipo
    if not audio.content_type.startswith('audio/') and not audio.filename.lower().endswith(('.wav','.mp3','.m4a','.webm','.ogg')):
        raise CustomError(status_code=status.HTTP_400_BAD_REQUEST, message='Unsupported_Audio_Format')
    try:
        contents = await audio.read()
        if len(contents) == 0:
            raise CustomError(status_code=status.HTTP_400_BAD_REQUEST, message='Empty_File')
        # Escribir a archivo temporal
        suffix = os.path.splitext(audio.filename)[1] or '.webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        model = _load_model(WHISPER_MODEL)
        segments, info = model.transcribe(tmp_path, beam_size=1)
        text = ' '.join([seg.text.strip() for seg in segments]).strip()
        os.unlink(tmp_path)
        return {
            'text': text,
            'language': info.language,
            'duration': info.duration,
            'model': WHISPER_MODEL,
            'private_mode': PRIVATE_MODE,
        }
    except CustomError:
        raise
    except Exception as e:
        raise CustomError(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message='Transcription_Error')

