# Déploiement Cleared2Bet — Oracle Cloud Free Tier (recommandé)

Oui : **Cleared2Bet tourne très bien sur Oracle Cloud Always Free**.
Tu as une vraie VM Linux (egress ouvert → SofaScore OK), contrairement à PythonAnywhere free.

Stack : **Ubuntu 22.04/24.04 (ARM Ampere)**, nginx, Gunicorn (systemd), Let’s Encrypt.  
Les fichiers dans `deploy/` sont les mêmes pour OVH ou tout autre VPS.

## Capacités Always Free (indicatif 2026)

| Ressource | Suffisant pour Cleared2Bet ? |
|-----------|------------------------------|
| **Ampere A1** jusqu’à **2 OCPU / 12 Go RAM** (quota tenancy) | Oui, largement |
| 2 × VM x86 `E2.1.Micro` (1 Go) | Possible mais serré (numpy/scipy) — **préférer Ampere** |
| IP publique, 80/443 | Oui (à ouvrir dans la Security List) |
| Sortie Internet (SofaScore) | Oui |

> Les quotas Always Free évoluent : vise **1 instance `VM.Standard.A1.Flex`**, ex. **2 OCPU / 12 Go** (ou 1 OCPU / 6 Go si tu partages le quota).

## 1. Créer l’instance OCI

1. [cloud.oracle.com](https://cloud.oracle.com) → **Compute → Instances → Create**.
2. **Image** : Canonical Ubuntu 22.04 ou 24.04 **aarch64**.
3. **Shape** : `VM.Standard.A1.Flex` (Always Free-eligible) — ex. 2 OCPU, 12 Go.
4. **Networking** : VCN par défaut + **Assign a public IPv4 address**.
5. **SSH key** : ajoute ta clé publique.
6. Create. Note l’**IP publique**.

### Security List / NSG (obligatoire)

Ingress sur le subnet de la VM :

| Port | Source | Usage |
|------|--------|--------|
| 22 | ton IP (idéalement) ou `0.0.0.0/0` | SSH |
| 80 | `0.0.0.0/0` | HTTP / Let’s Encrypt |
| 443 | `0.0.0.0/0` | HTTPS |

Sans ça, nginx/certbot restent injoignables même si `ufw` est ouvert.

### Capacité « Out of capacity »

Les régions free sont souvent saturées. Change d’**Availability Domain**, de **région**, ou réessaie plus tard (souvent la nuit EU).

## 2. Première connexion

```bash
ssh -i ~/.ssh/ta_cle ubuntu@IP_PUBLIQUE_OCI
```

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev nginx git \
  build-essential libpq-dev certbot python3-certbot-nginx
```

## 3. Application

```bash
sudo mkdir -p /var/www/cleared2bet
sudo chown "$USER":www-data /var/www/cleared2bet
cd /var/www/cleared2bet
git clone https://github.com/Stevy64/Cleared2Bet.git .

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

## 4. Gunicorn + systemd

```bash
sudo cp deploy/cleared2bet.service /etc/systemd/system/cleared2bet.service
sudo chown -R www-data:www-data /var/www/cleared2bet
sudo chmod 640 /var/www/cleared2bet/.env
sudo systemctl daemon-reload
sudo systemctl enable --now cleared2bet
sudo systemctl status cleared2bet
```

## 5. nginx + DNS + HTTPS

1. Remplace `cleared2bet.example.com` dans `deploy/nginx-cleared2bet.conf`.
2. DNS **A** (et AAAA si IPv6) → IP publique OCI.
3. Active nginx :

```bash
sudo cp deploy/nginx-cleared2bet.conf /etc/nginx/sites-available/cleared2bet
sudo ln -sf /etc/nginx/sites-available/cleared2bet /etc/nginx/sites-enabled/cleared2bet
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

4. Pare-feu OS + certificat :

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo certbot --nginx -d ton-domaine.com -d www.ton-domaine.com
```

## 6. SofaScore + cron

```bash
cd /var/www/cleared2bet
source .venv/bin/activate
set -a && source .env && set +a
python manage.py synchroniser_sofascore
python manage.py calculer_analyses
```

Cron (toutes les 2 h) :

```cron
0 */2 * * * cd /var/www/cleared2bet && . .venv/bin/activate && set -a && . ./.env && set +a && python manage.py synchroniser_sofascore && python manage.py calculer_analyses >> /var/log/cleared2bet-cron.log 2>&1
```

## 7. Mises à jour

```bash
cd /var/www/cleared2bet
sudo bash deploy/update.sh
```

## Checklist

- [ ] Instance Ampere Always Free + IP publique
- [ ] Security List : 22, 80, 443
- [ ] `.env` prod (`DEBUG=0`, vraie `SECRET_KEY`)
- [ ] `cleared2bet.service` actif
- [ ] DNS → IP OCI, nginx + Let’s Encrypt
- [ ] Sync SofaScore OK
- [ ] PWA en HTTPS sur mobile

## Alternative : VPS OVH

Même stack `deploy/` — voir [ovh-vps.md](ovh-vps.md) si tu préfères un VPS payant classique.
