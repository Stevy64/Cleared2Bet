# Cleared2Bet

Application web (PWA) d’aide à la décision pour les paris football. Elle affiche des **chances** et une **cote juste**. Elle ne promet pas de gain, ne prend pas de paris, et ne se connecte à aucun bookmaker.

## Installation

Python 3.10+ (3.12 recommandé).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
cp .env.example .env            # optionnel en local
python manage.py migrate
python manage.py createsuperuser
```

## Données

**Source de vérité : SofaScore** (calendrier réel). Ne jamais importer de JSON inventé en usage normal.

```bash
python manage.py synchroniser_sofascore
python manage.py calculer_analyses
python manage.py runserver
```

Un fichier `exemples/journee-2026-09-08.json` existe pour les **tests unitaires uniquement**. L’API publique ignore tout match sans `sofascore_id`.

```bash
python manage.py purger_matchs_fictifs
python manage.py importer_matchs --source exemples/journee-2026-09-08.json --allow-demo
python manage.py regler_options
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

CI : pytest, migrations, `collectstatic`, `check --deploy`, smoke VPS.

## Déploiement

Feuille de route : [docs/deploy.md](docs/deploy.md)

1. **PythonAnywhere** (maintenant, sans Docker) → [docs/pythonanywhere.md](docs/pythonanywhere.md)
2. **OVH Cloud** (proche avenir) → [docs/ovh-vps.md](docs/ovh-vps.md)  
   - Docker : [docs/docker.md](docs/docker.md) (`make prod-build`, images `cleared2bet-prod`)  
   - ou systemd + nginx

Moteur d’analyse **v3.1** (calibration marché par marché) : [docs/moteur-v31.md](docs/moteur-v31.md).

```bash
# Dev Docker
make dev-build
# → http://127.0.0.1:8000/   images : cleared2bet-dev

# Prod Docker (Postgres + Gunicorn + nginx)
cp .env.example .env   # SECRET_KEY + POSTGRES_PASSWORD
make prod-build
```
