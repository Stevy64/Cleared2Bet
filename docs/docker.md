# Docker — ZanalyZ

Stack alignée Makefile + images `zanalyz-dev` / `zanalyz-prod` / `zanalyz-moteur`.  
Prise en main générale : [getting-started.md](getting-started.md).

## Prérequis

- Docker Desktop (Windows/macOS) ou Docker Engine (Linux)
- `make` (Git Bash / WSL / Linux) — sinon utilise les `docker compose` ci-dessous

## Développement

Si le DNS/pip du daemon Docker est instable (fréquent sous Docker Desktop) :

```bash
make wheels-win               # ou make wheels (Linux/macOS)
# remplit ./wheels/ (gitignore) — le Dockerfile installe hors-ligne
```

```bash
cp .env.example .env          # optionnel en local
make dev-build                # build zanalyz-dev + runserver
# ou : docker compose -f docker-compose.dev.yml up --build
```

App : http://127.0.0.1:8000/  
Health : http://127.0.0.1:8000/health/  
Admin : http://127.0.0.1:8000/admin/

```bash
make superuser-dev
make migrate-dev
make sync-dev          # calendrier (sans H2H) + analyses
make sync-full-dev     # + contexte H2H/forme (plus lent)
make logs-dev
make stop-dev
```

SQLite persisté dans le volume `zanalyz_dev_data` (`/app/data/db.sqlite3`).

## Production (OVH Cloud / VPS Docker)

Stack micro-services : **nginx · web · moteur · worker · postgres · redis**  
→ détail [architecture.md](architecture.md)

```bash
cp .env.example .env
# Renseigne DJANGO_SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, CSRF…

make prod-build        # autonome : le worker tourne toutes les ~2 h
make superuser
make logs-worker
```

| Conteneur              | Image / rôle                         |
|------------------------|--------------------------------------|
| `zanalyz-web`      | `zanalyz-prod` (Gunicorn)        |
| `zanalyz-moteur`   | `zanalyz-moteur` (FastAPI)       |
| `zanalyz-worker`   | pipeline sync / analyse / règlement  |
| `zanalyz-db`       | Postgres 16                          |
| `zanalyz-redis`    | lock anti-chevauchement              |
| `zanalyz-nginx`    | reverse-proxy port 80                |

Dev avec worker : `make dev-worker` (profile Compose).

## PythonAnywhere

**Pas de Docker** sur PythonAnywhere. Déploie comme une app WSGI classique ([pythonanywhere.md](pythonanywhere.md)).  
Le Dockerfile sert surtout au **local** et à **OVH / VPS**.

## Commandes Makefile

```text
make help
make dev | dev-build | dev-d | stop-dev
make prod | prod-build | stop
make migrate[-dev] shell[-dev] superuser[-dev]
make sync[-dev] test collectstatic psql health clean
make wheels | wheels-win
```
