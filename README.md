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

## Déploiement (Oracle Cloud Free Tier — recommandé)

Guide : [docs/oracle-cloud.md](docs/oracle-cloud.md).  
Alternative VPS OVH : [docs/ovh-vps.md](docs/ovh-vps.md).

Fichiers dans `deploy/` : Gunicorn, systemd, nginx, `update.sh`.

```bash
cp .env.example .env
# Renseigne DJANGO_SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn --config deploy/gunicorn.conf.py config.wsgi:application
```

Ouvre `/` en HTTPS, installe la PWA. Hors ligne, le service worker sert la coque et les derniers matchs mis en cache.
