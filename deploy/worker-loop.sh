#!/bin/sh
# Worker autonome Cleared2Bet — sync → analyse → règlement → purge
# Tourne en boucle dans le container cleared2bet-worker.
set -eu

INTERVAL="${C2B_WORKER_INTERVAL:-7200}"
LOCK_KEY="${C2B_WORKER_LOCK_KEY:-c2b:worker:pipeline}"
LOCK_TTL="${C2B_WORKER_LOCK_TTL:-3600}"
REDIS_URL="${C2B_REDIS_URL:-}"

echo ">>> worker autonome (interval=${INTERVAL}s)"

acquire_lock() {
  if [ -z "$REDIS_URL" ]; then
    return 0
  fi
  python - <<'PY'
import os, sys
try:
    import redis
except ImportError:
    sys.exit(0)
url = os.environ.get("C2B_REDIS_URL", "")
key = os.environ.get("C2B_WORKER_LOCK_KEY", "c2b:worker:pipeline")
ttl = int(os.environ.get("C2B_WORKER_LOCK_TTL", "3600"))
r = redis.from_url(url)
ok = r.set(key, "1", nx=True, ex=ttl)
sys.exit(0 if ok else 1)
PY
}

release_lock() {
  if [ -z "$REDIS_URL" ]; then
    return 0
  fi
  python - <<'PY'
import os
try:
    import redis
except ImportError:
    raise SystemExit(0)
url = os.environ.get("C2B_REDIS_URL", "")
key = os.environ.get("C2B_WORKER_LOCK_KEY", "c2b:worker:pipeline")
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
  python manage.py synchroniser_sofascore --pages "${C2B_SYNC_PAGES:-1}" --passes "${C2B_SYNC_PASSES:-1}" --calculer \
    || echo "WARN sync/calcul échoué (on continue)"

  # Contexte terrain (plus lent) — toutes les N boucles si demandé
  if [ "${C2B_SYNC_CONTEXTE:-0}" = "1" ]; then
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
