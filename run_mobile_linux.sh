#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON_EXE="$(pwd)/.venv/bin/python"
[ -x "$PYTHON_EXE" ] || { echo "Execute setup_linux.sh primeiro."; exit 1; }
printf '%s\n' \
  "TMS Motorista disponivel na rede local:" \
  "http://IP_DO_COMPUTADOR:8000/motorista" \
  "Aviso: o GPS do celular normalmente exige HTTPS. Consulte RASTREAMENTO.md."
cd backend
"$PYTHON_EXE" -m app.scripts.update_database
"$PYTHON_EXE" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
