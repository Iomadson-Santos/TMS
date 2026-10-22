#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "Ambiente virtual ausente. Execute setup_linux.sh primeiro."
  exit 1
fi

cd backend
../.venv/bin/python -m app.scripts.upgrade_env_security
../.venv/bin/python -m app.scripts.update_database
echo "Atualizacao concluida com sucesso."
