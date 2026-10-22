#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/backend"

python -m app.scripts.security_check --config-only

# O plano gratuito nao oferece pre-deploy command. Na homologacao, as migracoes
# podem rodar no inicio. Em producao, o render.yaml usa predeploy_render.sh.
if [[ "${RUN_MIGRATIONS_ON_START:-false}" == "true" ]]; then
  python -m app.scripts.update_database
  python -m app.scripts.ensure_initial_admin
  python -m app.scripts.security_check
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --no-server-header
