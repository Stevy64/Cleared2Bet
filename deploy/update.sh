#!/usr/bin/env bash
# Déploiement / mise à jour ZanalyZ sur VPS (Ubuntu/Debian).
# Usage (depuis /var/www/zanalyz, en root ou sudo) :
#   bash deploy/update.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo "Manque .env — copie .env.example et renseigne les valeurs."
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if systemctl list-unit-files | grep -q '^zanalyz.service'; then
  systemctl restart zanalyz
  systemctl reload nginx || true
fi

echo "OK — ZanalyZ à jour."
