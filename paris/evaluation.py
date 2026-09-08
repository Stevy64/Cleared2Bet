def evaluer(code, fh, fa, hh=None, ha=None):
    """Une option est-elle gagnante ?

    fh, fa : buts finaux domicile / extérieur.
    hh, ha : buts à la mi-temps, facultatifs.
    Retourne True (gagné), False (perdu) ou None (impossible à trancher).
    """
    if fh is None or fa is None:
        return None
    total, ecart = fh + fa, fh - fa

    if code == '1X2_1': return ecart > 0
    if code == '1X2_N': return ecart == 0
    if code == '1X2_2': return ecart < 0
    if code == 'DC_1X': return ecart >= 0
    if code == 'DC_X2': return ecart <= 0
    if code == 'DC_12': return ecart != 0

    if code.startswith('OV_'): return total > float(code[3:])
    if code.startswith('UN_'): return total < float(code[3:])

    if code.startswith('MRG_'):
        _, cote, n = code.split('_')
        n = int(n)
        return (ecart >= n) if cote == 'H' else (-ecart >= n)

    if code.startswith('HCP_'):
        # « ne perd pas de plus de h buts » : perdre d'exactement h reste gagnant.
        # Le >= est le piège de toute cette fonction. Voir les tests.
        _, cote, h = code.split('_')
        h = int(h)                      # '+1' -> 1
        return (ecart + h >= 0) if cote == 'H' else (-ecart + h >= 0)

    if code.startswith('HT_'):
        if hh is None or ha is None: return None
        he, ht = hh - ha, hh + ha
        if code == 'HT_1': return he > 0
        if code == 'HT_N': return he == 0
        if code == 'HT_2': return he < 0
        if code.startswith('HT_OV_'): return ht > float(code[6:])
        if code.startswith('HT_UN_'): return ht < float(code[6:])

    if code == 'BTTS_O': return fh > 0 and fa > 0
    if code == 'BTTS_N': return not (fh > 0 and fa > 0)
    if code == 'DOM_MARQUE': return fh > 0
    if code == 'EXT_MARQUE': return fa > 0

    raise ValueError(f"code inconnu : {code}")
