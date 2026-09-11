#!/bin/sh
# Worker autonome ZanalyZ — sync → analyse → règlement → purge
# Tourne en boucle dans le container zanalyz-worker.
set -eu

INTERVAL="${ZANALYZ_WORKER_INTERVAL:-${C2B_WORKER_INTERVAL:-7200}}"
LOCK_KEY="${ZANALYZ_WORKER_LOCK_KEY:-${C2B_WORKER_LOCK_KEY:-zanalyz:worker:pipeline}}"
LOCK_TTL="${ZANALYZ_WORKER_LOCK_TTL:-${C2B_WORKER_LOCK_TTL:-3600}}"
REDIS_URL="${ZANALYZ_REDIS_URL:-${C2B_REDIS_URL:-}}"

echo ">>> worker autonome (interval=${INTERVAL}s)"

acquire_lock() {
  if [ -z "$REDIS_URL" ]; then
    return 0
  fi
  ZANALYZ_REDIS_URL="$REDIS_URL" \
  ZANALYZ_WORKER_LOCK_KEY="$LOCK_KEY" \
  ZANALYZ_WORKER_LOCK_TTL="$LOCK_TTL" \
  python - <<'PY'
import os, sys
try:
    import redis
except ImportError:
    sys.exit(0)
url = os.environ.get("ZANALYZ_REDIS_URL", "")
key = os.environ.get("ZANALYZ_WORKER_LOCK_KEY", "zanalyz:worker:pipeline")
ttl = int(os.environ.get("ZANALYZ_WORKER_LOCK_TTL", "3600"))
r = redis.from_url(url)
ok = r.set(key, "1", nx=True, ex=ttl)
sys.exit(0 if ok else 1)
PY
}

release_lock() {
  if [ -z "$REDIS_URL" ]; then
    return 0
  fi
  ZANALYZ_REDIS_URL="$REDIS_URL" \
  ZANALYZ_WORKER_LOCK_KEY="$LOCK_KEY" \
  python - <<'PY'
import os
try:
    import redis
except ImportError:
    raise SystemExit(0)
url = os.environ.get("ZANALYZ_REDIS_URL", "")
key = os.environ.get("ZANALYZ_WORKER_LOCK_KEY", "zanalyz:worker:pipeline")
r = redis.from_url(url)
r.delete(key)
PY
}

run_pipeline() {
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) pipeline ==="
  if ! acquire_lock; then
    echo ">>> lock actif — skip ce tour"
    return 0
  fi
  # shellcheck disable=SC2064
  trap release_lock EXIT

  echo ">>> synchroniser_sofascore + calculer"
  python manage.py synchroniser_sofascore --pages "${ZANALYZ_SYNC_PAGES:-${C2B_SYNC_PAGES:-1}}" --passes "${ZANALYZ_SYNC_PASSES:-${C2B_SYNC_PASSES:-1}}" --calculer \
    || echo "WARN sync/calcul échoué (on continue)"

  # Contexte terrain (plus lent) — toutes les N boucles si demandé
  if [ "${ZANALYZ_SYNC_CONTEXTE:-${C2B_SYNC_CONTEXTE:-0}}" = "1" ]; then
    echo ">>> sync contexte"
    python manage.py synchroniser_sofascore --pages 1 --passes 0 --contexte \
      || echo "WARN contexte échoué"
  fi

  echo ">>> regler_options --apprendre"
  python manage.py regler_options --apprendre \
    || echo "WARN règlement échoué"

  echo ">>> purger_chat"
  python manage.py purger_chat \
    || echo "WARN purge chat échoué"

  release_lock
  trap - EXIT
  echo "=== pipeline OK ==="
}

# Premier passage immédiat puis boucle
run_pipeline
while true; do
  echo ">>> sleep ${INTERVAL}s"
  sleep "$INTERVAL"
  run_pipeline
done
