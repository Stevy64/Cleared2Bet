# Déploiement Cleared2Bet sur VPS OVH Cloud

Stack cible : **Ubuntu 22.04/24.04**, nginx, Gunicorn (systemd), Let’s Encrypt.
SofaScore fonctionne en sortie libre (pas de whitelist PythonAnywhere).

## 1. Prérequis serveur

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev nginx git \
  build-essential libpq-dev certbot python3-certbot-nginx
```

Crée le répertoire app :

```bash
sudo mkdir -p /var/www/cleared2bet
sudo chown "$USER":www-data /var/www/cleared2bet
cd /var/www/cleared2bet
git clone https://github.com/Stevy64/Cleared2Bet.git .
```

## 2. Environnement

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

cp .env.example .env
nano .env   # SECRET_KEY, ALLOWED_HOSTS, CSRF, domaine OVH
```

Génère une clé :

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Exemple `.env` :

```bash
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=…
DJANGO_ALLOWED_HOSTS=ton-domaine.com,www.ton-domaine.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://ton-domaine.com,https://www.ton-domaine.com
DJANGO_SSL=1
```

SQLite suffit pour démarrer. Postgres :

```bash
# DJANGO_DB_URL=postgres://c2b:pass@127.0.0.1:5432/cleared2bet
pip install "psycopg[binary]>=3.2"
```

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 3. Gunicorn + systemd

Adapte `deploy/cleared2bet.service` si le chemin n’est pas `/var/www/cleared2bet`.

```bash
sudo cp deploy/cleared2bet.service /etc/systemd/system/cleared2bet.service
sudo mkdir -p /run/cleared2bet
sudo chown www-data:www-data /var/www/cleared2bet -R
# Le socket est créé par RuntimeDirectory=cleared2bet (user www-data)
sudo systemctl daemon-reload
sudo systemctl enable --now cleared2bet
sudo systemctl status cleared2bet
```

Vérifie que `www-data` peut lire le code et écrire la DB SQLite si utilisée :

```bash
sudo chown -R www-data:www-data /var/www/cleared2bet
sudo chmod 640 /var/www/cleared2bet/.env
```

## 4. nginx + HTTPS

1. Remplace `cleared2bet.example.com` dans `deploy/nginx-cleared2bet.conf` par ton domaine OVH.
2. Pointe le DNS A/AAAA du domaine vers l’IP du VPS.
3. Active le site :

```bash
sudo cp deploy/nginx-cleared2bet.conf /etc/nginx/sites-available/cleared2bet
sudo ln -sf /etc/nginx/sites-available/cleared2bet /etc/nginx/sites-enabled/cleared2bet
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

4. Certificat :

```bash
sudo certbot --nginx -d ton-domaine.com -d www.ton-domaine.com
```

## 5. Données moteur (SofaScore)

Sur le VPS (egress ouvert) :

```bash
cd /var/www/cleared2bet
source .venv/bin/activate
set -a && source .env && set +a
python manage.py synchroniser_sofascore
python manage.py calculer_analyses
python manage.py regler_options
```

Cron (user `www-data` ou root avec le venv) — ex. toutes les 2 h :

```cron
0 */2 * * * cd /var/www/cleared2bet && . .venv/bin/activate && set -a && . ./.env && set +a && python manage.py synchroniser_sofascore && python manage.py calculer_analyses >> /var/log/cleared2bet-cron.log 2>&1
```

## 6. Mises à jour

```bash
cd /var/www/cleared2bet
sudo -u www-data git pull   # ou en tant que propriétaire du clone
sudo bash deploy/update.sh
```

## 7. Pare-feu OVH / ufw

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## Checklist prod

- [ ] `.env` avec `DEBUG=0` et vraie `SECRET_KEY`
- [ ] Domaine DNS → IP VPS
- [ ] `cleared2bet.service` active
- [ ] nginx + TLS
- [ ] `collectstatic` fait
- [ ] Sync SofaScore OK
- [ ] PWA / HTTPS OK sur mobile
