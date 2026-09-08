# Cleared2Bet

Application web (PWA) d’aide à la décision pour les paris football. Elle affiche des **chances** et une **cote juste**. Elle ne promet pas de gain, ne prend pas de paris, et ne se connecte à aucun bookmaker.

## Installation

Python 3.10+ (3.12 recommandé). Sur PythonAnywhere, choisis **python3.10** (ou 3.12)
pour le virtualenv — voir [docs/pythonanywhere.md](docs/pythonanywhere.md).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # pour l’admin et la saisie de scores
```

## Données

**Source de vérité : SofaScore** (calendrier réel). Ne jamais importer de JSON inventé en usage normal.

```bash
python manage.py synchroniser_sofascore
python manage.py calculer_analyses
python manage.py runserver
```

Un fichier `exemples/journee-2026-09-08.json` existe pour les **tests unitaires uniquement**. Il contient des matchs **fictifs** (ex. Man Utd–Everton, Lille–Nice). L’API publique ignore tout match sans `sofascore_id`. Pour nettoyer une base polluée :

```bash
python manage.py purger_matchs_fictifs
```

Import JSON démo (interdit sans confirmation explicite) :

```bash
python manage.py importer_matchs --source exemples/journee-2026-09-08.json --allow-demo
```

Les commandes acceptent `--dry-run`. Après un match, saisis le score dans l’admin (ou Réglages si tu es connecté) puis :

```bash
python manage.py regler_options
```

Un cron peut enchaîner sync SofaScore → calcul → règlement.

## Tests

```bash
pytest
```

CI GitHub Actions (`.github/workflows/ci.yml`) : pytest, migrations, `collectstatic`,
`manage.py check --deploy`, smoke PythonAnywhere (`DEBUG=0`).

## Déploiement (PythonAnywhere)

Voir [docs/pythonanywhere.md](docs/pythonanywhere.md).

```bash
export DJANGO_DEBUG=0
export DJANGO_SECRET_KEY=...
export DJANGO_ALLOWED_HOSTS=gabomazone.pythonanywhere.com
export DJANGO_SSL=1
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Alternative locale / VPS : `gunicorn config.wsgi:application`.

Ouvre `/` sur le téléphone, installe la PWA. Hors ligne, le service worker sert la coque et les derniers matchs mis en cache.
