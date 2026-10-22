#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON_EXE="$(pwd)/.venv/bin/python"
[ -x "$PYTHON_EXE" ] || { echo "Execute setup_linux.sh primeiro."; exit 1; }

cd backend
PYTHONPATH=. "$PYTHON_EXE" -m compileall -q app tests alembic
PYTHONPATH=. "$PYTHON_EXE" -m pytest -q
"$PYTHON_EXE" -m ruff check app tests alembic --select E9,F63,F7,F82
"$PYTHON_EXE" -m bandit -q -ll -r app -x tests -s B105,B106,B107
"$PYTHON_EXE" -m pip_audit -r requirements.txt
cd ..

if command -v node >/dev/null 2>&1; then
  for file in frontend/assets/js/*.js; do
    node --check "$file"
  done
else
  echo "[AVISO] Node.js ausente; a sintaxe JavaScript nao foi verificada."
fi

echo "Revisao automatizada concluida sem falhas."
