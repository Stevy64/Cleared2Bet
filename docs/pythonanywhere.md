# Déploiement Cleared2Bet sur PythonAnywhere

## Python

Utilise **Python 3.10** minimum (3.12 si proposé dans le sélecteur de venv).
Les pins `numpy==2.2.6` / `scipy==1.15.3` sont compatibles 3.10–3.13.

Création du venv (exemple) :

```bash
mkvirtualenv --python=/usr/bin/python3.10 cleared2bet
# ou via l’UI : Web → Virtualenv → python3.10
```

## Variables d’environnement (Web app → WSGI / virtualenv)

```bash
export DJANGO_DEBUG=0
export DJANGO_SECRET_KEY='…clé longue aléatoire…'
export DJANGO_ALLOWED_HOSTS='gabomazone.pythonanywhere.com'
export DJANGO_SSL=1
```

## Commandes après chaque pull

```bash
cd ~/Cleared2Bet
source ~/.virtualenvs/cleared2bet/bin/activate   # adapte le nom du venv
git pull
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py synchroniser_sofascore   # cron recommandé
python manage.py calculer_analyses
```

## WSGI (exemple)

Dans le fichier WSGI PythonAnywhere :

```python
import os
import sys

path = '/home/Gabomazone/Cleared2Bet'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
# Définis aussi DJANGO_DEBUG / SECRET_KEY / ALLOWED_HOSTS via l’UI PA
# ou ici avant get_wsgi_application().

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## Static

- URL : `/static/`
- Directory : `/home/Gabomazone/Cleared2Bet/staticfiles` (après `collectstatic`)
  ou le chemin `STATIC_ROOT` de ton `settings.py`.

## Cron (recommandé)

1. `python manage.py synchroniser_sofascore`
2. `python manage.py calculer_analyses`
3. `python manage.py regler_options`

## CI

Le workflow GitHub Actions (`.github/workflows/ci.yml`) exécute tests, migrations,
`collectstatic` et un smoke `DEBUG=0` avec l’hôte PythonAnywhere (dont Python 3.10).
