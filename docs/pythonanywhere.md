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
# Si quota OK (optionnel, sync SofaScore plus fiable) :
# pip install "curl_cffi>=0.7.0"
python manage.py migrate --noinput
python manage.py collectstatic --noinput
# Obligatoire : sans collectstatic, CSS/JS = page blanche en prod (DEBUG=0).
python manage.py synchroniser_sofascore   # cron recommandé
python manage.py calculer_analyses
```

Si `Disk quota exceeded` ou SciPy cassé (`libscipy_openblas`) :

```bash
pip cache purge
pip uninstall -y scipy numpy
# Libère de la place (anciens venvs, caches) :
# rm -rf ~/Cleared2Bet/.venv-r2b
# rm -rf ~/.cache/pip
du -sh ~/* ~/Cleared2Bet/.* 2>/dev/null | sort -h | tail

# Réinstalle sans remplir le cache pip
pip install --no-cache-dir numpy==2.2.6 scipy==1.15.3
```

Puis :

```bash
git pull
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Dans l’onglet **Web** PythonAnywhere :
- Virtualenv : chemin vers ton `.venv-c2b` (ou venv)
- Static files : URL `/static/` → Directory `/home/Gabomazone/Cleared2Bet/staticfiles`
- Puis **Reload**

WhiteNoise sert aussi les static via WSGI si le mapping manque.

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
