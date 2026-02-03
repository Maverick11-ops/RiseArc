#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/code/risearc-env"
STREAMLIT_BIN="$VENV_DIR/bin/streamlit"

if [[ -f "$ROOT_DIR/variables.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/variables.env"
  set +a
fi

if [[ ! -x "$STREAMLIT_BIN" ]]; then
  echo "Streamlit not found at $STREAMLIT_BIN"
  echo "Make sure the local venv exists or install Streamlit." 
  exit 1
fi

APP_URL="http://127.0.0.1:8501"

if [[ -z "${NEMOTRON_URL:-}" ]]; then
  echo "Note: NEMOTRON_URL is not set."
  echo "Set it in variables.env or export it before running to enable Nemotron."
fi

if [[ -z "${NEMOTRON_MODEL:-}" ]]; then
  echo "Note: NEMOTRON_MODEL is not set. Defaulting to 'local-model'."
fi

"$STREAMLIT_BIN" run "$ROOT_DIR/code/app/streamlit_chat.py" \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port 8501 &

STREAMLIT_PID=$!

sleep 1

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$APP_URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$APP_URL" >/dev/null 2>&1 || true
fi

echo "RiseArc is running at $APP_URL"

wait "$STREAMLIT_PID"
