#!/bin/sh
set -e

echo ">>> ZanalyZ entrypoint"

if [ "${ZANALYZ_SKIP_MIGRATE:-${C2B_SKIP_MIGRATE:-0}}" != "1" ]; then
  echo ">>> migrate"
  python manage.py migrate --noinput
fi

if [ "${ZANALYZ_SKIP_COLLECTSTATIC:-${C2B_SKIP_COLLECTSTATIC:-0}}" != "1" ] && [ "${DJANGO_DEBUG:-0}" != "1" ]; then
  echo ">>> collectstatic"
  python manage.py collectstatic --noinput
fi

echo ">>> exec: $*"
exec "$@"
