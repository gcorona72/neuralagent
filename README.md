![NeuralAgent](docs/images/neuralagent_logo.png)

NeuralAgent (fork) – guía rápida para ejecutarlo localmente en macOS/Windows y con extras (voz y adjuntos).

Resumen
- Backend: FastAPI + SQLModel (Postgres o SQLite local por defecto)
- Desktop: Electron + React
- Agente: Python (pyautogui) que controla mouse/teclado y envía/recibe pasos via API
- Novedades en este fork: entrada por voz (Web Speech API) y subida de archivos al hilo como memoria.

Requisitos básicos
- Python 3.11+ (recomendado 3.12)
- Node 18+
- npm 9+
- macOS (Intel/Apple Silicon) o Windows 10+

1) Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

Config mínima del .env:
- Si tienes Postgres, completa DB_* o DB_CONNECTION_STRING.
- Si NO tienes Postgres, no pongas nada: el backend usará SQLite local (./neuralagent.db).
- Configura un proveedor LLM: por ejemplo, OpenAI
  - OPENAI_API_KEY=...
  - CLASSIFIER_AGENT_MODEL_TYPE=openai
  - CLASSIFIER_AGENT_MODEL_ID=gpt-4o-mini
  - TITLE_AGENT_MODEL_TYPE=openai
  - TITLE_AGENT_MODEL_ID=gpt-4o-mini
  - SUGGESTOR_AGENT_MODEL_TYPE=openai
  - SUGGESTOR_AGENT_MODEL_ID=gpt-4o-mini
  - PLANNER_AGENT_MODEL_TYPE=openai
  - PLANNER_AGENT_MODEL_ID=gpt-4o
  - COMPUTER_USE_AGENT_MODEL_TYPE=anthropic
  - COMPUTER_USE_AGENT_MODEL_ID=claude-3-7-sonnet-20250219  # o bedrock/azure según tu cuenta

Inicializa DB y arranca:
```bash
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2) Desktop (Electron + React)

```bash
cd desktop
npm install
cd neuralagent-app
cp .env.example .env
# Edita .env:
# REACT_APP_PROTOCOL=http
# REACT_APP_WEBSOCKET_PROTOCOL=ws
# REACT_APP_DNS=127.0.0.1:8000
cd ..
npm start
```

Notas macOS:
- Este repo ajusta el puerto del React dev server a 6763 con cross-env, ya incluido.
- La app Electron arrancará cuando el frontend esté disponible.

3) Agente Python (desktop/aiagent)

```bash
cd desktop/aiagent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# En macOS, permite permisos de accesibilidad para controlar mouse/teclado (Sistema > Privacidad > Accesibilidad).
deactivate
```

Inicio de sesión
- Puedes usar el flujo “Login with Google” (requiere configurar GOOGLE_LOGIN_CLIENT_ID/SECRET en el backend),
  o usar signup/login por email en la UI.

Uso básico
- Crea un Thread y escribe una tarea. Si es de tipo “desktop task”, el agente Python se lanzará y empezará a actuar.
- Background mode en Windows usa WSL (no disponible aún en macOS).

Funciones añadidas en este fork
- Voz: botón de micrófono en la vista de Thread que usa Web Speech API para dictar el mensaje.
- Adjuntos: botón de clip para subir un archivo; el contenido (texto) o metadatos se guardan como memoria del task activo.

Solución de problemas
- Si React no abre/puerto distinto: verifica que REACT_APP_DNS=127.0.0.1:8000 y que el backend está en 8000.
- Modelos LLM: si falta configuración, algunas rutas fallarán. Completa .env del backend.
- SQLite: si no tienes Postgres, el backend crea neuralagent.db en la carpeta backend.

## LLM por defecto y fallback

En modo `PRIVATE_MODE=true` o si faltan las variables de entorno de modelo, el backend usa un LLM local de respaldo (DummyLocalLLM) que:
- Clasifica tareas básicas (inquiry vs desktop_task)
- Genera títulos simples
- Devuelve subtareas mínimas
Esto permite usar la app sin claves externas.

Para activar OpenAI por defecto copia `backend/.env.example` a `backend/.env` y ajusta:
```
OPENAI_API_KEY=tu_clave
CLASSIFIER_AGENT_MODEL_TYPE=openai
CLASSIFIER_AGENT_MODEL_ID=gpt-4o-mini
TITLE_AGENT_MODEL_TYPE=openai
TITLE_AGENT_MODEL_ID=gpt-4o-mini
PLANNER_AGENT_MODEL_TYPE=openai
PLANNER_AGENT_MODEL_ID=gpt-4o-mini
SUGGESTOR_AGENT_MODEL_TYPE=openai
SUGGESTOR_AGENT_MODEL_ID=gpt-4o-mini
COMPUTER_USE_AGENT_MODEL_TYPE=openai
COMPUTER_USE_AGENT_MODEL_ID=gpt-4o
```
Si prefieres Anthropic o Bedrock cambia el TYPE y el ID y define la clave correspondiente.

## Script de desarrollo rápido

Para arrancar/gestionar backend + Electron con un solo comando se añadió `scripts/dev.sh`.

Dar permisos de ejecución una sola vez:
```bash
chmod +x scripts/dev.sh
```

Comandos:
```bash
scripts/dev.sh start    # Inicia backend (background) y luego Electron (foreground)
scripts/dev.sh status   # Muestra procesos/puertos
scripts/dev.sh stop     # Detiene backend, react y electron
scripts/dev.sh restart  # stop + start
```

Variables opcionales (antes del start):
```bash
export BACKEND_PORT=8000
export FRONT_PORT=6763
```

Si quieres sólo backend:
```bash
scripts/dev.sh stop
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Licencia
MIT
