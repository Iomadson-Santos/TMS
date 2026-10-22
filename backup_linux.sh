#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

PYTHON_EXE="$(pwd)/.venv/bin/python"
if [ ! -x "$PYTHON_EXE" ]; then
  echo "Ambiente virtual ausente. Execute setup_linux.sh primeiro."
  exit 1
fi

cd backend
"$PYTHON_EXE" -m app.scripts.backup_database
