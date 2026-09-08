# Exemples JSON

Les fichiers de ce dossier sont **fictifs** : ils servent aux tests et au format d’import documenté.

Ils ne représentent **pas** le calendrier réel. Ne les importe jamais en base de prod
sans `--allow-demo`, et préfère toujours :

```bash
python manage.py synchroniser_sofascore
```

L’API n’expose que les matchs ayant un `sofascore_id`.
