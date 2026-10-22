#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
printf "Informe a URL HTTPS do TMS: "
read -r TMS_URL
python3 smoke_test_online.py --url "$TMS_URL" --login
