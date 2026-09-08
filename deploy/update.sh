#!/usr/bin/env bash
# Déploiement / mise à jour Cleared2Bet sur VPS (Ubuntu/Debian).
# Usage (depuis /var/www/cleared2bet, en root ou sudo) :
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

if systemctl list-unit-files | grep -q '^cleared2bet.service'; then
  systemctl restart cleared2bet
  systemctl reload nginx || true
fi

echo "OK — Cleared2Bet à jour."
