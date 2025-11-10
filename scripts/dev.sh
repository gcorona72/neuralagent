#!/usr/bin/env bash
set -euo pipefail

# dev.sh — utilidades para arrancar/parar el entorno local (backend + Electron)
# Uso:
#   scripts/dev.sh start      # inicia backend (bg) + Electron (fg)
#   scripts/dev.sh stop       # detiene backend y procesos electron/react
#   scripts/dev.sh status     # muestra estado de puertos/procesos
#   scripts/dev.sh restart    # stop + start
#
# Requisitos: macOS, bash, lsof

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
DESKTOP_DIR="$ROOT_DIR/desktop"
FRONT_APP_DIR="$DESKTOP_DIR/neuralagent-app"

BACKEND_PORT=${BACKEND_PORT:-8000}
FRONT_PORT=${FRONT_PORT:-6763}

log() { echo "[dev.sh] $*"; }
warn() { echo "[dev.sh][WARN] $*" >&2; }

is_port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

kill_port() {
  local port="$1"
  if is_port_in_use "$port"; then
    local pids
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t | tr '\n' ' ' || true)
    if [[ -n "${pids:-}" ]]; then
      log "Matando procesos en puerto $port: $pids"
      kill -9 $pids || true
    fi
  fi
}

start_backend() {
  log "Iniciando backend en $BACKEND_DIR (puerto $BACKEND_PORT)"
  cd "$BACKEND_DIR"
  if [[ ! -d .venv ]]; then
    log "Creando venv .venv"
    python -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt >/dev/null

  # Exportar variables del .env si existe
  if [[ -f .env ]]; then
    set +u
    set -a
    # shellcheck disable=SC1091
    source .env || true
    set +a
    set -u
  fi
  export PRIVATE_MODE="${PRIVATE_MODE:-true}"
  export LOCAL_STORAGE_DIR="${LOCAL_STORAGE_DIR:-$BACKEND_DIR/local_storage}"
  mkdir -p "$LOCAL_STORAGE_DIR/uploads" "$LOCAL_STORAGE_DIR/screenshots"

  # Liberar puerto si está ocupado
  kill_port "$BACKEND_PORT" || true

  log "Lanzando uvicorn..."
  PYTHONPATH="$BACKEND_DIR" uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" --reload \
    > "$BACKEND_DIR/.dev_backend.log" 2>&1 &
  echo $! > "$BACKEND_DIR/.dev_backend.pid"
  log "Backend PID $(cat "$BACKEND_DIR/.dev_backend.pid")"
}

stop_backend() {
  cd "$BACKEND_DIR"
  if [[ -f .dev_backend.pid ]]; then
    local pid
    pid=$(cat .dev_backend.pid || true)
    if [[ -n "${pid:-}" ]]; then
      log "Deteniendo backend PID $pid"
      kill -9 "$pid" 2>/dev/null || true
      rm -f .dev_backend.pid
    fi
  fi
  kill_port "$BACKEND_PORT" || true
}

start_desktop() {
  log "Iniciando Electron + React en $DESKTOP_DIR (React puerto $FRONT_PORT)"
  cd "$DESKTOP_DIR"
  export BROWSER=none
  # Asegurar deps
  npm install >/dev/null
  # Si puerto ocupado, matar procesos típicos
  kill_port "$FRONT_PORT" || true
  pkill -f "react-scripts start" 2>/dev/null || true
  pkill -f "electron .*${DESKTOP_DIR}" 2>/dev/null || true

  # Ejecuta en primer plano; termina con Ctrl+C
  npm run start
}

stop_desktop() {
  pkill -f "react-scripts start" 2>/dev/null || true
  pkill -f "wait-on http://localhost:${FRONT_PORT}" 2>/dev/null || true
  pkill -f "electron .*${DESKTOP_DIR}" 2>/dev/null || true
  kill_port "$FRONT_PORT" || true
  log "Desktop detenido"
}

status() {
  echo "--- STATUS ---"
  if is_port_in_use "$BACKEND_PORT"; then
    echo "Backend escuchando en :$BACKEND_PORT (uvicorn)"
    lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN
  else
    echo "Backend no está escuchando en :$BACKEND_PORT"
  fi
  if is_port_in_use "$FRONT_PORT"; then
    echo "Frontend React escuchando en :$FRONT_PORT"
    lsof -nP -iTCP:"$FRONT_PORT" -sTCP:LISTEN
  else
    echo "Frontend no está escuchando en :$FRONT_PORT"
  fi
  # Electron
  if pgrep -f "electron .*${DESKTOP_DIR}" >/dev/null 2>&1; then
    echo "Electron en ejecución:"
    pgrep -fl "electron .*${DESKTOP_DIR}"
  else
    echo "Electron no está en ejecución"
  fi
}

start_all() {
  start_backend
  start_desktop
}

stop_all() {
  stop_desktop || true
  stop_backend || true
}

case "${1:-}" in
  start) start_all ;;
  stop) stop_all ;;
  restart) stop_all; start_all ;;
  status) status ;;
  *)
    echo "Uso: $0 {start|stop|restart|status}"
    exit 1
    ;;
 esac

