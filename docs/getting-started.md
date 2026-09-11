# Prise en main — Cleared2Bet

Guide pour lancer le projet en local et comprendre le flux quotidien.

## 1. Prérequis

- Git, Python 3.11+ **ou** Docker Desktop / Engine  
- Sous Windows : `make` via Git Bash / WSL, ou recopier les commandes `docker compose` de [docker.md](docker.md)

## 2. Premier démarrage (Docker)

```bash
git clone https://github.com/Stevy64/Cleared2Bet.git
cd Cleared2Bet
cp .env.example .env
```

Si le build Docker échoue sur `pip install` (DNS) :

```bash
make wheels-win    # Windows + venv local
# ou make wheels   # Linux/macOS
```

Puis :

```bash
make dev-d
make migrate-dev
make superuser-dev
```

Ouvre http://127.0.0.1:8000/ et connecte-toi à `/admin/`.

### Remplir le calendrier

```bash
make sync-dev
```

Équivalent manuel :

```bash
docker compose -f docker-compose.dev.yml exec web \
  python manage.py synchroniser_sofascore --pages 1
docker compose -f docker-compose.dev.yml exec web \
  python manage.py calculer_analyses
```

Contexte terrain (forme / H2H / absents) — plus lent, optionnel :

```bash
make sync-full-dev
```

## 3. Comptes & VIP

1. Créer un superuser (`make superuser-dev`).  
2. Dans l’admin : utilisateurs → profil → activer VIP (durée / expiration).  
3. Réglages site : numéro WhatsApp + message pour la demande VIP.

Rôles côté app :

| Catégorie | Accès |
|-----------|--------|
| Visiteur | Liste matchs, tips sans justifs |
| Membre | + votes / propositions |
| VIP | + justifications, Salon VIP |

## 4. Pages utiles

| URL | Rôle |
|-----|------|
| `/` | Matchs du jour |
| `/salon` | Chat VIP |
| `/admin/` | Back-office |
| `/health/` | Sonde load-balancer |
| `:8001/health` | Sonde moteur (Docker) |

## 5. Développement sans Docker

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
pytest
```

Le moteur peut rester local (pas de `C2B_MOTEUR_URL`). Pour tester le micro-service :

```bash
uvicorn moteur_service.app:app --reload --port 8001
# .env : C2B_MOTEUR_URL=http://127.0.0.1:8001
```

## 6. Flux données (résumé)

```text
Sync calendrier / cotes
        ↓
Moteur v3.1 → tips (prudente / équilibrée / audacieuse / filet)
        ↓
App PWA + votes utilisateurs
        ↓
Règlement après match (+ apprentissage calibration)
```

Fiches clubs : chaîne de secours logos / forme si l’API calendrier principale est indisponible (détails techniques dans le code, non exposés à l’UI).

## 7. Commandes fréquentes

```bash
make help
make logs-dev
make logs-moteur
make health
make stop-dev
make clean                 # volumes / images (destructif)
```

## 8. Ensuite

- Déploiement : [deploy.md](deploy.md)  
- Prod Docker : [docker.md](docker.md)  
- Architecture : [architecture.md](architecture.md)
