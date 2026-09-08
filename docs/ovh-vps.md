# Déploiement Cleared2Bet sur VPS OVH (alternative)

La cible **recommandée** est **Oracle Cloud Free Tier** :

→ **[docs/oracle-cloud.md](oracle-cloud.md)**

Sur OVH, la stack est **identique** (`deploy/` : nginx + Gunicorn + systemd).  
Différences : pas de Security List OCI ; tu ouvres 80/443 via le pare-feu OVH / `ufw`, et tu pointes le DNS vers l’IP du VPS.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev nginx git \
  build-essential libpq-dev certbot python3-certbot-nginx

sudo mkdir -p /var/www/cleared2bet
sudo chown "$USER":www-data /var/www/cleared2bet
cd /var/www/cleared2bet
git clone https://github.com/Stevy64/Cleared2Bet.git .

python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -r requirements.txt
cp .env.example .env && nano .env

python manage.py migrate --noinput
python manage.py collectstatic --noinput

sudo cp deploy/cleared2bet.service /etc/systemd/system/
sudo chown -R www-data:www-data /var/www/cleared2bet
sudo systemctl daemon-reload && sudo systemctl enable --now cleared2bet

# Adapter le domaine dans deploy/nginx-cleared2bet.conf puis :
sudo cp deploy/nginx-cleared2bet.conf /etc/nginx/sites-available/cleared2bet
sudo ln -sf /etc/nginx/sites-available/cleared2bet /etc/nginx/sites-enabled/cleared2bet
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d ton-domaine.com

sudo bash deploy/update.sh   # mises à jour ultérieures
```

SofaScore / cron : mêmes commandes que dans [oracle-cloud.md](oracle-cloud.md).
