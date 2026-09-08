"""Validation du JSON d'import. Un fichier invalide doit tout faire échouer."""

CHAMPS_MATCH = (
    'competition', 'domicile', 'exterieur', 'coup_denvoi', 'cotes',
)
CHAMPS_EQUIPE = ('nom', 'nom_court', 'slug')
CHAMPS_COMPETITION = ('code', 'nom')
CHAMPS_COTES = ('1X2',)


class ImportInvalide(ValueError):
    pass


def _exige(obj, champs, ou):
    if not isinstance(obj, dict):
        raise ImportInvalide(f'{ou} doit être un objet JSON.')
    manquants = [c for c in champs if c not in obj]
    if manquants:
        raise ImportInvalide(f'{ou} : champs manquants {manquants}.')


def _cote_positive(valeur, ou):
    try:
        n = float(valeur)
    except (TypeError, ValueError) as exc:
        raise ImportInvalide(f'{ou} : cote invalide {valeur!r}.') from exc
    if n <= 1:
        raise ImportInvalide(f'{ou} : cote {n} ≤ 1, refusée.')
    return n


def valider_payload(data):
    if not isinstance(data, dict) or 'matchs' not in data:
        raise ImportInvalide('La racine doit être un objet avec une clé "matchs".')
    matchs = data['matchs']
    if not isinstance(matchs, list) or not matchs:
        raise ImportInvalide('"matchs" doit être une liste non vide.')
    valides = []
    for i, m in enumerate(matchs):
        ou = f'matchs[{i}]'
        _exige(m, CHAMPS_MATCH, ou)
        _exige(m['competition'], CHAMPS_COMPETITION, f'{ou}.competition')
        _exige(m['domicile'], CHAMPS_EQUIPE, f'{ou}.domicile')
        _exige(m['exterieur'], CHAMPS_EQUIPE, f'{ou}.exterieur')
        if m['domicile']['slug'] == m['exterieur']['slug']:
            raise ImportInvalide(f'{ou} : domicile et extérieur identiques.')
        cotes = m['cotes']
        _exige(cotes, CHAMPS_COTES, f'{ou}.cotes')
        unx2 = cotes['1X2']
        _exige(unx2, ('1', 'N', '2'), f'{ou}.cotes.1X2')
        for sel in ('1', 'N', '2'):
            _cote_positive(unx2[sel], f'{ou}.cotes.1X2.{sel}')
        ou25 = cotes.get('OU25')
        if ou25 is not None:
            _exige(ou25, ('over', 'under'), f'{ou}.cotes.OU25')
            _cote_positive(ou25['over'], f'{ou}.cotes.OU25.over')
            _cote_positive(ou25['under'], f'{ou}.cotes.OU25.under')
        if not m.get('coup_denvoi'):
            raise ImportInvalide(f'{ou} : coup_denvoi obligatoire.')
        valides.append(m)
    return valides
