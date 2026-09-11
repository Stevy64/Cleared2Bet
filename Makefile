# ════════════════════════════════════════════
# Cleared2Bet — Commandes simplifiées
# Usage : make <commande>
# Images : cleared2bet-dev, cleared2bet-prod
# ════════════════════════════════════════════

COMPOSE_DEV  = docker compose -f docker-compose.dev.yml
COMPOSE_PROD = docker compose -f docker-compose.yml

.PHONY: help wheels wheels-win dev dev-build dev-d dev-worker prod prod-build build stop stop-dev \
	migrate migrate-dev shell shell-dev superuser superuser-dev \
	logs logs-dev logs-web logs-worker logs-moteur clean test collectstatic sync sync-dev \
	sync-full-dev psql health

help:
	@echo "Commandes Cleared2Bet :"
	@echo "  make wheels / wheels-win - Prefetch wheels Docker"
	@echo "  make dev-build      - web + moteur (+ redis)"
	@echo "  make dev-worker     - active le worker autonome (profile)"
	@echo "  make prod-build     - stack prod (web/moteur/worker/db/redis/nginx)"
	@echo "  make logs-moteur / logs-worker"
	@echo "  make snapshot-export-dev / snapshot-import-dev"
	@echo "  make sync[-dev]     - pipeline manuel"
	@echo "  make health / clean"
	@echo "  Doc : docs/architecture.md / docs/pythonanywhere.md"

# Wheels Linux pour build Docker (évite DNS/pip flaky dans le daemon)
wheels:
	mkdir -p wheels
	pip download -r requirements.txt -d wheels \
		--platform manylinux_2_17_x86_64 \
		--platform manylinux2014_x86_64 \
		--implementation cp --python-version 311 --abi cp311 \
		--only-binary=:all:
	pip download "typing-extensions>=4.6" -d wheels --only-binary=:all:

wheels-win:
	mkdir -p wheels
	.\.venv\Scripts\python.exe -m pip download -r requirements.txt -d wheels \
		--platform manylinux_2_17_x86_64 \
		--platform manylinux2014_x86_64 \
		--implementation cp --python-version 311 --abi cp311 \
		--only-binary=:all:
	.\.venv\Scripts\python.exe -m pip download "typing-extensions>=4.6" -d wheels --only-binary=:all:

dev:
	$(COMPOSE_DEV) up

dev-build:
	$(COMPOSE_DEV) up --build

dev-d:
	$(COMPOSE_DEV) up -d --build

dev-worker:
	$(COMPOSE_DEV) --profile worker up -d --build

prod:
	$(COMPOSE_PROD) up -d

prod-build:
	$(COMPOSE_PROD) up -d --build

build:
	$(COMPOSE_DEV) build --no-cache
	$(COMPOSE_PROD) build --no-cache

stop:
	$(COMPOSE_PROD) down

stop-dev:
	$(COMPOSE_DEV) down

migrate:
	$(COMPOSE_PROD) exec web python manage.py migrate --noinput

migrate-dev:
	$(COMPOSE_DEV) exec web python manage.py migrate --noinput

shell:
	$(COMPOSE_PROD) exec web python manage.py shell

shell-dev:
	$(COMPOSE_DEV) exec web python manage.py shell

superuser:
	$(COMPOSE_PROD) exec web python manage.py createsuperuser

superuser-dev:
	$(COMPOSE_DEV) run --rm web python manage.py createsuperuser

logs:
	$(COMPOSE_PROD) logs -f

logs-dev:
	$(COMPOSE_DEV) logs -f

logs-web:
	$(COMPOSE_PROD) logs -f web

logs-worker:
	$(COMPOSE_PROD) logs -f worker

logs-moteur:
	$(COMPOSE_PROD) logs -f moteur

collectstatic:
	$(COMPOSE_PROD) exec web python manage.py collectstatic --noinput --clear

sync:
	$(COMPOSE_PROD) exec web sh -c "\
		python manage.py synchroniser_sofascore --calculer && \
		python manage.py regler_options --apprendre && \
		python manage.py purger_chat"

sync-dev:
	$(COMPOSE_DEV) exec web sh -c "\
		python manage.py synchroniser_sofascore --pages 1 --passes 1 --calculer && \
		python manage.py regler_options --apprendre && \
		python manage.py purger_chat"

sync-full-dev:
	$(COMPOSE_DEV) exec web sh -c "\
		python manage.py synchroniser_sofascore --contexte --calculer && \
		python manage.py regler_options --apprendre && \
		python manage.py purger_chat"

snapshot-export-dev:
	$(COMPOSE_DEV) exec web python manage.py exporter_snapshot --out exports/matchs.json --jours 21 --enrichir-clubs

snapshot-import-dev:
	$(COMPOSE_DEV) exec web python manage.py importer_snapshot --source exports/matchs.json

test:
	$(COMPOSE_DEV) exec web python manage.py test --verbosity=2

psql:
	$(COMPOSE_PROD) exec db psql -U $${POSTGRES_USER:-cleared2bet} $${POSTGRES_DB:-cleared2bet}

health:
	@curl -sf http://127.0.0.1:$${C2B_DEV_PORT:-8000}/health/ && echo OK || \
	 curl -sf http://127.0.0.1:$${C2B_HTTP_PORT:-80}/health/ && echo OK

clean:
	$(COMPOSE_DEV) down -v --remove-orphans
	$(COMPOSE_PROD) down -v --remove-orphans
