# Docker — Cleared2Bet

Stack alignée sur Gabomazone : **Makefile** + images `cleared2bet-dev` / `cleared2bet-prod`.

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
make dev-build                # build cleared2bet-dev + runserver
# ou : docker compose -f docker-compose.dev.yml up --build
```

App : http://127.0.0.1:8000/  
Health : http://127.0.0.1:8000/health/  
Admin : http://127.0.0.1:8000/admin/

```bash
make superuser-dev
make migrate-dev
make sync-dev          # SofaScore + analyses + tips
make logs-dev
make stop-dev
```

SQLite persisté dans le volume `cleared2bet_dev_data` (`/app/data/db.sqlite3`).

## Production (OVH Cloud / VPS Docker)

```bash
cp .env.example .env
# Renseigne DJANGO_SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, CSRF…

make prod-build        # cleared2bet-prod + Postgres + nginx
make superuser
make sync
make logs
```

Services :

| Conteneur            | Image / rôle              |
|----------------------|---------------------------|
| `cleared2bet-web`    | `cleared2bet-prod` (Gunicorn) |
| `cleared2bet-db`     | Postgres 16               |
| `cleared2bet-nginx`  | reverse-proxy port 80     |

TLS : termine HTTPS devant nginx (Certbot sur l’hôte, ou Caddy, ou load-balancer OVH), puis `DJANGO_SSL=1` + `CSRF_TRUSTED_ORIGINS=https://…`.

Sans Docker sur le VPS : guide classique [ovh-vps.md](ovh-vps.md) (systemd + nginx).

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
