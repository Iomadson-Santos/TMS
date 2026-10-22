#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/backend"

python -m app.scripts.security_check --config-only
python -m app.scripts.update_database
python -m app.scripts.ensure_initial_admin
python -m app.scripts.security_check
