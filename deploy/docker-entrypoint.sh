#!/bin/sh
set -e

echo ">>> Cleared2Bet entrypoint"

if [ "${C2B_SKIP_MIGRATE:-0}" != "1" ]; then
  echo ">>> migrate"
  python manage.py migrate --noinput
fi

if [ "${C2B_SKIP_COLLECTSTATIC:-0}" != "1" ] && [ "${DJANGO_DEBUG:-0}" != "1" ]; then
  echo ">>> collectstatic"
  python manage.py collectstatic --noinput
fi

echo ">>> exec: $*"
exec "$@"
