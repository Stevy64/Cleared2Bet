# Déployer Cleared2Bet sur PythonAnywhere

Guide **pas à pas** pour une mise en ligne rapide (compte Beginner ou payant).  
**Pas de Docker** sur PythonAnywhere — app WSGI classique.

> **Limite importante (compte gratuit)** : le proxy sortant est **whitelisté**.  
> SofaScore n’est en général **pas** joignable → `synchroniser_sofascore` échouera.  
> Tu peux quand même tester l’UI, l’admin, le VIP, le salon.  
> Pour la sync live : passe sur **OVH Cloud** ([ovh-vps.md](ovh-vps.md) ou [docker.md](docker.md)).

---

## 1. Préparer le dépôt sur GitHub

Sur ta machine (déjà fait si tu as pushé) :

```bash
git clone https://github.com/Stevy64/Cleared2Bet.git
cd Cleared2Bet
```

Sur PythonAnywhere : Dashboard → **Consoles** → **Bash**.

```bash
cd ~
git clone https://github.com/Stevy64/Cleared2Bet.git
cd Cleared2Bet
```

Mises à jour plus tard :

```bash
cd ~/Cleared2Bet
git pull
```

---

## 2. Virtualenv + dépendances

PythonAnywhere propose souvent **3.10** ou **3.11** (évite 3.13 pour numpy/scipy).

```bash
cd ~/Cleared2Bet
# Remplace 3.11 par la version disponible : python3.10, python3.11…
python3.11 -m venv ~/.virtualenvs/cleared2bet
source ~/.virtualenvs/cleared2bet/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Vérifie :

```bash
python -c "import django; print(django.get_version())"
```

---

## 3. Fichier `.env`

```bash
cd ~/Cleared2Bet
cp .env.example .env
nano .env
```

Valeurs typiques (remplace `TONUSER`) :

```bash
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=…   # génère : python -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_ALLOWED_HOSTS=TONUSER.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://TONUSER.pythonanywhere.com
DJANGO_SSL=1
DJANGO_SECURE_SSL_REDIRECT=0
# SQLite suffit sur PA :
# (laisse POSTGRES_* commentés / inutilisés)
```

`DJANGO_SECURE_SSL_REDIRECT=0` : PythonAnywhere gère déjà HTTPS devant ton app.

---

## 4. Migrations + static + superuser

```bash
cd ~/Cleared2Bet
source ~/.virtualenvs/cleared2bet/bin/activate
set -a && source .env && set +a

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Base SQLite : `db.sqlite3` à la racine du projet (ou le chemin de `DJANGO_SQLITE_PATH` si tu le définis).

---

## 5. Web app WSGI (interface PythonAnywhere)

1. Onglet **Web** → **Add a new web app**  
   - Manual configuration  
   - Même version Python que le venv (ex. 3.11)
2. **Code** :
   - **Source code** : `/home/TONUSER/Cleared2Bet`
   - **Working directory** : `/home/TONUSER/Cleared2Bet`
3. **Virtualenv** : `/home/TONUSER/.virtualenvs/cleared2bet`
4. **WSGI configuration file** → édite (remplace le contenu par défaut) :

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

5. **Static files** (onglet Web → Static files) :

| URL        | Directory                                      |
|------------|------------------------------------------------|
| `/static/` | `/home/TONUSER/Cleared2Bet/staticfiles`        |

(Optionnel si tu sers aussi les assets source : `/static/` → `…/static` — en prod `collectstatic` + `staticfiles` suffit avec WhiteNoise / mapping PA.)

6. Bouton **Reload** de la web app.

Ouvre `https://TONUSER.pythonanywhere.com/` et `/admin/`.  
Health : `https://TONUSER.pythonanywhere.com/health/` → `{"status":"ok","app":"cleared2bet"}`.

---

## 6. Scheduled tasks (optionnel)

Onglet **Tasks** (compte payant souvent requis pour un cron fiable) :

```bash
cd ~/Cleared2Bet && source ~/.virtualenvs/cleared2bet/bin/activate && set -a && source .env && set +a && python manage.py synchroniser_sofascore && python manage.py calculer_analyses && python manage.py regler_options --apprendre && python manage.py purger_chat
```

Sur **Beginner** : lance à la main dans une console Bash quand tu veux tester (souvent bloqué par la whitelist).

---

## 7. Après un `git pull`

```bash
cd ~/Cleared2Bet
source ~/.virtualenvs/cleared2bet/bin/activate
git pull
pip install -r requirements.txt
set -a && source .env && set +a
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Puis **Reload** dans l’onglet Web.

---

## Checklist PythonAnywhere

- [ ] Clone + venv + `pip install -r requirements.txt`
- [ ] `.env` avec `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` = `TONUSER.pythonanywhere.com`
- [ ] `migrate` + `collectstatic` + superuser
- [ ] WSGI + Virtualenv + Static `/static/` → `staticfiles`
- [ ] Reload + `/health/` OK
- [ ] (Accepté) sync SofaScore peut échouer sur free tier

---

## Suite : OVH Cloud

Quand tu veux la prod réelle (SofaScore + Postgres + Docker ou systemd) :

1. Court terme classique : [ovh-vps.md](ovh-vps.md)  
2. Même stack qu’en local Docker : [docker.md](docker.md) (`make prod-build`)
