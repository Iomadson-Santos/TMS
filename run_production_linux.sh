#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON_EXE="$(pwd)/.venv/bin/python"
[ -x "$PYTHON_EXE" ] || { echo "Execute setup_linux.sh primeiro."; exit 1; }
FORWARDED_ALLOW_IPS="${TMS_FORWARDED_ALLOW_IPS:-127.0.0.1}"

cd backend
"$PYTHON_EXE" -m app.scripts.security_check --config-only
"$PYTHON_EXE" -m app.scripts.update_database
"$PYTHON_EXE" -m app.scripts.security_check

exec "$PYTHON_EXE" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips="$FORWARDED_ALLOW_IPS" \
  --no-server-header \
  --timeout-keep-alive 5 \
  --limit-concurrency 500
