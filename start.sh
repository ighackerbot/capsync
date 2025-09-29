#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

random_free_port() {
  local start=$1
  local end=$2
  while true; do
    local port=$(( RANDOM % (end - start + 1) + start ))
    if ! lsof -i ":${port}" >/dev/null 2>&1; then
      echo "$port"
      return 0
    fi
  done
}

BACKEND_PORT="${BACKEND_PORT:-$(random_free_port 8000 8999)}"
FRONTEND_PORT="${FRONTEND_PORT:-$(random_free_port 5173 5999)}"

echo "Using backend port: $BACKEND_PORT"
echo "Using frontend port: $FRONTEND_PORT"

# ---------- Backend: FastAPI (faster-whisper) ----------
echo "[backend] ensuring Python 3.11 venv and deps..."
cd "$ROOT_DIR/server"
if ! command -v /opt/homebrew/bin/python3.11 >/dev/null 2>&1; then
  echo "Python 3.11 not found at /opt/homebrew/bin/python3.11. Install with: brew install python@3.11" >&2
  exit 1
fi

/opt/homebrew/bin/python3.11 -m venv .venv || true
source .venv/bin/activate
pip -q install --upgrade pip
pip -q install -r requirements.txt

echo "[backend] starting uvicorn on 127.0.0.1:${BACKEND_PORT}..."
export WHISPER_MODEL="${WHISPER_MODEL:-small}"
nohup uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" > "$ROOT_DIR/server.out" 2>&1 &
BACK_PID=$!
echo "[backend] pid=$BACK_PID (logs: $ROOT_DIR/server.out)"

# ---------- Frontend: Vite (Remotion UI) ----------
echo "[frontend] installing deps if needed..."
cd "$ROOT_DIR/app"
npm install --silent

echo "[frontend] starting Vite on http://localhost:${FRONTEND_PORT} ..."
export VITE_API_BASE="http://127.0.0.1:${BACKEND_PORT}"
nohup npm run dev -- --port "$FRONTEND_PORT" > "$ROOT_DIR/app.out" 2>&1 &
FRONT_PID=$!
echo "[frontend] pid=$FRONT_PID (logs: $ROOT_DIR/app.out)"

echo ""
echo "Ready!"
echo "- API:     http://127.0.0.1:${BACKEND_PORT} (docs at /docs)"
echo "- Frontend: http://localhost:${FRONTEND_PORT}"
echo ""
if command -v open >/dev/null 2>&1; then
  open "http://localhost:${FRONTEND_PORT}"
fi

echo "To stop: kill $BACK_PID $FRONT_PID"


