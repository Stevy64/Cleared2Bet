# Format d'import JSON — Cleared2Bet

> **Attention** : cet import est réservé aux **démos / tests**. En usage normal,
> les matchs viennent uniquement de `synchroniser_sofascore`. Un JSON inventé
> (comme `exemples/journee-2026-09-08.json`) détruit la confiance s’il est
> importé en base : l’API n’expose désormais que les matchs avec `sofascore_id`.

Un fichier contient une clé `matchs` : liste non vide. L'import est **tout ou rien** :
si un match est invalide, rien n'est écrit.

```json
{
  "matchs": [
    {
      "competition": {
        "code": "UCL",
        "nom": "Ligue des champions",
        "pays": "Europe",
        "ordre": 10
      },
      "domicile": {
        "nom": "Paris Saint-Germain",
        "nom_court": "PSG",
        "slug": "psg"
      },
      "exterieur": {
        "nom": "FC Barcelone",
        "nom_court": "Barça",
        "slug": "barcelone"
      },
      "coup_denvoi": "2026-09-08T21:00:00+02:00",
      "journee": "Phase de ligue",
      "statut": "a_venir",
      "releve_le": "2026-09-08T12:00:00+02:00",
      "cotes": {
        "bookmaker": "consensus",
        "1X2": { "1": 2.15, "N": 3.60, "2": 3.20 },
        "OU25": { "over": 1.72, "under": 2.15 }
      },
      "contexte": {
        "forme_dom": "V V N D V",
        "forme_ext": "V V V N D",
        "absents_dom": "",
        "absents_ext": "",
        "tendance_buts": "Les deux attaquent.",
        "a_savoir": "",
        "confrontations": "",
        "fiabilite": "moyenne",
        "source": "notes personnelles"
      }
    }
  ]
}
```

## Obligatoire

- `competition.code`, `competition.nom`
- `domicile` / `exterieur` : `nom`, `nom_court`, `slug` (slugs distincts)
- `coup_denvoi` : ISO 8601
- `cotes.1X2.1`, `.N`, `.2` : nombres **strictement supérieurs à 1**

## Facultatif

- `cotes.OU25.over` / `under` (si présent, les deux)
- `cotes.bookmaker` (défaut `consensus`)
- `journee`, `statut`, `releve_le`, `contexte.*`
- `competition.pays`, `ordre`, `actif`

Clé d'idempotence d'un match : `domicile` + `exterieur` + `coup_denvoi`.
