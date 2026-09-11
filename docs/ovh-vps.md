# Déploiement Cleared2Bet sur VPS OVH Cloud (recommandé)

Cible **production** : egress libre → SofaScore OK, TLS, cron, Postgres possible.

Deux chemins :

| Chemin | Quand l’utiliser | Doc |
|--------|------------------|-----|
| **Docker** (`make prod`) | Recommandé si tu as déjà utilisé `cleared2bet-dev` en local | [docker.md](docker.md) |
| **systemd + nginx** | VPS classique sans Docker | sections ci-dessous |

Fichiers prêts : `deploy/gunicorn.conf.py`, `deploy/cleared2bet.service`,
`deploy/nginx-cleared2bet.conf`, `deploy/nginx-docker.conf`, `deploy/update.sh`,
`docker-compose.yml`, `Makefile`.

---

## A. Chemin Docker (proche avenir / recommandé)

Sur le VPS Ubuntu (Docker Engine + Compose plugin) :

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-v2
sudo usermod -aG docker "$USER"   # puis reconnecte-toi en SSH

sudo mkdir -p /var/www/cleared2bet
sudo chown "$USER":"$USER" /var/www/cleared2bet
cd /var/www/cleared2bet
git clone https://github.com/Stevy64/Cleared2Bet.git .

cp .env.example .env
nano .env
```

Renseigne au minimum :

```bash
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=…
DJANGO_ALLOWED_HOSTS=ton-domaine.com,www.ton-domaine.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://ton-domaine.com,https://www.ton-domaine.com
DJANGO_SSL=1
POSTGRES_PASSWORD=…   # fort
C2B_HTTP_PORT=80
```

```bash
# Optionnel si le réseau du build est fragile :
# make wheels && make prod-build
make prod-build
make superuser
make sync
```

Services : `cleared2bet-web` (image `cleared2bet-prod`), `cleared2bet-db`, `cleared2bet-nginx`.

TLS : Certbot sur l’hôte (proxy vers le port nginx), ou load-balancer OVH, puis `DJANGO_SSL=1`.  
Détails Makefile / health : [docker.md](docker.md).

Mises à jour :

```bash
cd /var/www/cleared2bet
git pull
make prod-build
```

---

## B. Chemin classique (systemd + nginx, sans Docker)

Stack : **Ubuntu 22.04/24.04**, nginx, Gunicorn (systemd), Let’s Encrypt.

### 1. Prérequis

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev nginx git \
  build-essential libpq-dev certbot python3-certbot-nginx

sudo mkdir -p /var/www/cleared2bet
sudo chown "$USER":www-data /var/www/cleared2bet
cd /var/www/cleared2bet
git clone https://github.com/Stevy64/Cleared2Bet.git .
```

### 2. Environnement

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

cp .env.example .env
nano .env
```

```bash
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=…   # python -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_ALLOWED_HOSTS=ton-domaine.com,www.ton-domaine.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://ton-domaine.com,https://www.ton-domaine.com
DJANGO_SSL=1
```

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 3. Gunicorn + systemd

```bash
sudo cp deploy/cleared2bet.service /etc/systemd/system/cleared2bet.service
sudo chown -R www-data:www-data /var/www/cleared2bet
sudo chmod 640 /var/www/cleared2bet/.env
sudo systemctl daemon-reload
sudo systemctl enable --now cleared2bet
sudo systemctl status cleared2bet
```

### 4. nginx + HTTPS

1. Remplace `cleared2bet.example.com` dans `deploy/nginx-cleared2bet.conf`.
2. DNS A → IP du VPS OVH.
3. Active le site :

```bash
sudo cp deploy/nginx-cleared2bet.conf /etc/nginx/sites-available/cleared2bet
sudo ln -sf /etc/nginx/sites-available/cleared2bet /etc/nginx/sites-enabled/cleared2bet
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
sudo certbot --nginx -d ton-domaine.com -d www.ton-domaine.com
```

### 5. Données + apprentissage moteur

Après chaque sync / règlement, le moteur **affine** `data/calibration.json`
à partir des tips déjà gagnés ou perdus.

```bash
cd /var/www/cleared2bet
source .venv/bin/activate
set -a && source .env && set +a

python manage.py synchroniser_sofascore
python manage.py calculer_analyses
python manage.py regler_options --apprendre
```

Cron (toutes les 2 h) :

```cron
0 */2 * * * cd /var/www/cleared2bet && . .venv/bin/activate && set -a && . ./.env && set +a && python manage.py synchroniser_sofascore && python manage.py calculer_analyses && python manage.py regler_options --apprendre && python manage.py purger_chat >> /var/log/cleared2bet-cron.log 2>&1
```

### 6. Mises à jour

```bash
cd /var/www/cleared2bet
sudo bash deploy/update.sh
```

---

## Checklist OVH

- [ ] DNS A → VPS
- [ ] `.env` prod (SECRET_KEY, ALLOWED_HOSTS, CSRF, SSL)
- [ ] Docker **ou** `cleared2bet.service` + nginx + TLS
- [ ] Sync SofaScore + analyses + règlement
- [ ] PWA HTTPS OK (`/health/` → ok)

## Avant OVH : PythonAnywhere

Pour un premier essai UI/admin sans VPS : [pythonanywhere.md](pythonanywhere.md)  
(sync SofaScore souvent bloquée sur le free tier).

## Autre hébergeur

Oracle Cloud Free Tier : [oracle-cloud.md](oracle-cloud.md).
