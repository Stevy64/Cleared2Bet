# Déployer Cleared2Bet sur PythonAnywhere

Guide **pas à pas** (compte Beginner ou payant).  
**Pas de Docker** sur PythonAnywhere — app WSGI classique.

> **Pourquoi aucun match ?** Sur le free tier, la sync calendrier live est
> souvent **bloquée** (egress whitelist). Solution : générer les données **en
> local** (Docker / PC), les pousser sur Git, puis les **importer** sur PA.

---

## Données matchs via Git (recommandé)

### A. Sur ta machine (où la sync marche)

```bash
# Docker
make sync-dev
make snapshot-export-dev
# → exports/matchs.json

# ou sans Docker
python manage.py synchroniser_sofascore --pages 1 --calculer
python manage.py exporter_snapshot --out exports/matchs.json --jours 21
```

Puis commit + push :

```bash
git add exports/matchs.json
git commit -m "Refresh match snapshot for PythonAnywhere"
git push
```

Le fichier contient matchs, cotes, analyses / tips déjà calculés.  
L’UI PA n’a **pas besoin** de recalculer ni d’appeler d’API calendrier.

### B. Sur PythonAnywhere

```bash
cd ~/Cleared2Bet
source ~/.virtualenvs/cleared2bet/bin/activate
git pull
set -a && source .env && set +a
python manage.py importer_snapshot --source exports/matchs.json
```

Optionnel (si le snapshot n’a que les cotes, sans analyses) :

```bash
python manage.py importer_snapshot --source exports/matchs.json --recalculer
```

Recharge la page Matchs (vide le cache navigateur si besoin).  
Le filtre date doit correspondre à des matchs présents dans le snapshot  
(`--jours 21` autour d’aujourd’hui couvre en général « Aujourd’hui »).

### Routine

| Fréquence | Action |
|-----------|--------|
| Chez toi | `make sync-dev` → `make snapshot-export-dev` → commit/push |
| Sur PA | `git pull` → `importer_snapshot` |

Sans `C2B_MOTEUR_URL` sur PA : le moteur tourne **dans Django** si tu utilises `--recalculer`.

---

## 1. Clone

```bash
cd ~
git clone https://github.com/Stevy64/Cleared2Bet.git
cd Cleared2Bet
```

---

## 2. Virtualenv + dépendances

Python **3.10** ou **3.11**.

```bash
cd ~/Cleared2Bet
python3.11 -m venv ~/.virtualenvs/cleared2bet
source ~/.virtualenvs/cleared2bet/bin/activate
pip install -U pip
pip install -r requirements.txt
```

---

## 3. `.env`

```bash
cp .env.example .env
nano .env
```

```bash
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=…   # secrets.token_urlsafe(50)
DJANGO_ALLOWED_HOSTS=TONUSER.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://TONUSER.pythonanywhere.com
DJANGO_SSL=1
DJANGO_SECURE_SSL_REDIRECT=0
# Pas de C2B_MOTEUR_URL
```

---

## 4. Migrate + static + snapshot

```bash
source ~/.virtualenvs/cleared2bet/bin/activate
set -a && source .env && set +a
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser   # si pas déjà fait
python manage.py importer_snapshot --source exports/matchs.json
```

Les **logos** sont des URLs CDN chargées par le **navigateur** (pas le serveur PA).  
Les **fiches club** (blason) viennent du champ embarqué dans le snapshot.  
« Consensus — » = pas encore de votes utilisateurs (normal).

---

## 5. Web app WSGI

1. **Web** → Manual configuration → même Python que le venv  
2. Source / working dir : `/home/TONUSER/Cleared2Bet`  
3. Virtualenv : `/home/TONUSER/.virtualenvs/cleared2bet`  
4. WSGI :

```python
import os
import sys
from dotenv import load_dotenv

project_home = "/home/TONUSER/Cleared2Bet"
if project_home not in sys.path:
    sys.path.insert(0, project_home)
load_dotenv(os.path.join(project_home, ".env"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

5. Static `/static/` → `…/staticfiles` ; Media `/media/` → `…/media`  
6. **Reload** — health : `/health/`

---

## Suite

Prod autonome Docker : [docker.md](docker.md) · [ovh-vps.md](ovh-vps.md)
