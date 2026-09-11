# Architecture micro-services ZanalyZ

L’app peut tourner **de façon autonome** sur le serveur : sync calendrier →
analyse moteur → tips → règlement → purge chat, sans action manuelle.

## Schéma

```text
                    ┌─────────────┐
   Internet ───────►│   nginx     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ zanalyz │  PWA + API + Admin
                    │    -web     │  (Gunicorn / Django)
                    └──────┬──────┘
                           │ HTTP analyse
                    ┌──────▼──────┐
                    │ zanalyz │  Moteur v3.1 (FastAPI)
                    │   -moteur   │  stateless CPU
                    └─────────────┘

        ┌──────────────────────────────────────┐
        │ zanalyz-worker (boucle ~2 h)     │
        │  1. sync calendrier (+ calculer)     │
        │  2. regler_options --apprendre       │
        │  3. purger_chat                      │
        │  lock Redis anti-chevauchement       │
        └───────────┬──────────────────────────┘
                    │
         ┌──────────▼──────────┐     ┌─────────┐
         │ zanalyz-db      │     │  redis  │
         │ (Postgres)          │     │  lock   │
         └─────────────────────┘     └─────────┘
```

## Granularité (volontairement limitée)

| Service | Image | Rôle |
|--------|-------|------|
| **nginx** | nginx | TLS/HTTP, static / media |
| **web** | `zanalyz-prod` | UI + API + admin |
| **moteur** | `zanalyz-moteur` | Calculs probabilités / tips |
| **worker** | `zanalyz-prod` | Pipeline autonome |
| **db** | postgres | Données |
| **redis** | redis | Lock jobs + présence Salon VIP |

Pas de découpage plus fin (auth service, etc.) : surcoût sans gain pour cette app.

## Variables clés

```bash
ZANALYZ_MOTEUR_URL=http://moteur:8001
ZANALYZ_REDIS_URL=redis://redis:6379/0
ZANALYZ_WORKER_INTERVAL=7200          # secondes entre deux pipelines
ZANALYZ_SYNC_PAGES=1
ZANALYZ_SYNC_CONTEXTE=0               # 1 = H2H/forme (plus lent)
```

Si `ZANALYZ_MOTEUR_URL` est vide, Django calcule **en local** (fallback).

## Lancer

```bash
# Prod
cp .env.example .env   # secrets
make prod-build        # web + moteur + worker + db + redis + nginx

# Dev (web + moteur ; worker optionnel)
make dev-d
make dev-worker        # profile Compose
```

## API moteur

- `GET  /health`
- `POST /v1/analyser` — lot de matchs + classement journée
- `POST /v1/analyser-un` — un match
- Docs OpenAPI : `http://moteur:8001/docs` (réseau Docker)

## Fiches clubs / logos

Chaîne côté serveur (noms de fournisseurs **non exposés** à l’UI) :

1. API calendrier principale  
2. Secours TheSportsDB (logos, forme, classement)  
3. Historique local en base  

Proxy logos : `GET /api/v1/equipes/<id>/logo/`

## PythonAnywhere

Pas de Docker : pas de worker container. Utilise les **Tasks** PA ou un cron
externe qui appelle les mêmes `manage.py` (voir [pythonanywhere.md](pythonanywhere.md)).
