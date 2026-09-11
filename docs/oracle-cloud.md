# Oracle Cloud Free Tier (alternative)

La cible **recommandée** est un **VPS OVH** :

→ **[docs/ovh-vps.md](ovh-vps.md)**

Sur Oracle Cloud Always Free, la stack `deploy/` est la même (nginx + Gunicorn).  
Particularités OCI : ouvrir **22 / 80 / 443** dans la **Security List** du VCN, image Ubuntu **ARM Ampere** (`VM.Standard.A1.Flex`).

Voir l’ancien guide détaillé ci-dessous si tu restes sur OCI.

## Créer l’instance (rappel)

1. Compute → Instance Ampere A1 Flex (ex. 2 OCPU / 12 Go).
2. IP publique + Security List 22/80/443.
3. Puis suivre les mêmes étapes qu’OVH : clone, `.env`, systemd, nginx, certbot, cron.

SofaScore fonctionne (egress libre). En cas d’« Out of capacity », change d’AD / région.
