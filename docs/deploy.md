# Déploiement — feuille de route

Ordre conseillé :

1. **Maintenant — PythonAnywhere** : UI, admin, VIP, sans Docker.  
   → [pythonanywhere.md](pythonanywhere.md)  
   ⚠️ Sync SofaScore souvent impossible sur le compte gratuit (whitelist).

2. **Proche avenir — OVH Cloud** : prod réelle.  
   - Docker (même images `cleared2bet-*` qu’en local) → [docker.md](docker.md) + section A de [ovh-vps.md](ovh-vps.md)  
   - ou systemd + nginx → section B de [ovh-vps.md](ovh-vps.md)

3. **Local** : `make dev-build` → [docker.md](docker.md)

Healthcheck partout : `GET /health/` → `{"status":"ok","app":"cleared2bet"}`.
