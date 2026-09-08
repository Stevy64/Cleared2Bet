# Cleared2Bet

Application web (PWA) d’aide à la décision pour les paris football. Elle affiche des **chances** et une **cote juste**. Elle ne promet pas de gain, ne prend pas de paris, et ne se connecte à aucun bookmaker.

## Installation

Python 3.12+ recommandé.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # pour l’admin et la saisie de scores
```

## Données

Le JSON d’import est décrit dans `docs/format_import.md`. Exemple réel de journée :

```bash
python manage.py importer_matchs --source exemples/journee-2026-09-08.json
python manage.py calculer_analyses --journee 2026-09-08
python manage.py runserver
```

Les trois commandes acceptent `--dry-run`. Après un match, saisis le score dans l’admin (ou Réglages si tu es connecté) puis :

```bash
python manage.py regler_options
```

Un cron peut enchaîner import → calcul → règlement.

## Tests

```bash
pytest
```

## Déploiement

`collectstatic` + gunicorn, rien d’autre (pas de build front).

```bash
set DJANGO_DEBUG=0
set DJANGO_SECRET_KEY=...
set DJANGO_ALLOWED_HOSTS=ton.domaine
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

PostgreSQL en production : renseigne `DATABASES` dans `config/settings.py` (SQLite suffit en local).

Ouvre `/` sur le téléphone, installe la PWA. Hors ligne, le service worker sert la coque et les derniers matchs mis en cache.
