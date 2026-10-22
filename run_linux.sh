#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON_EXE="$(pwd)/.venv/bin/python"
[ -x "$PYTHON_EXE" ] || { echo "Execute setup_linux.sh primeiro."; exit 1; }
cd backend
"$PYTHON_EXE" -m app.scripts.update_database
"$PYTHON_EXE" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
