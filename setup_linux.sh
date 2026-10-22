#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
PYTHON_EXE="$(pwd)/.venv/bin/python"
"$PYTHON_EXE" -m pip install --upgrade pip
"$PYTHON_EXE" -m pip install -r backend/requirements.txt
cd backend
[ -f .env ] || cp .env.example .env
"$PYTHON_EXE" -m app.scripts.update_database
"$PYTHON_EXE" -m app.scripts.seed
printf '\nInstalacao concluida. Execute ./run_linux.sh\n'
