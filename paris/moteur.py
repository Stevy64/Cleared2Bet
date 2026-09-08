"""
Moteur de probabilités Cleared2Bet — fonctions pures, sans Django.

Pipeline
--------
1. Cotes 1X2 (et optionnellement Over/Under 2.5) → probabilités sans marge (de-vig).
2. Ajustement de λ domicile / extérieur (Poisson + correction Dixon–Coles).
3. Matrice de scores → options de marchés (totaux, handicaps, mi-temps, etc.).
4. Calibration empirique sur les marchés *calculés* (pas sur le 1X2 marché).
5. Sélection journée : 1 tip par bande (prudente / équilibrée / audacieuse) + filet.

Conventions importantes
-----------------------
- RHO négatif (−0.06) : forme « moderne » où 0-0 / 1-1 sont renforcés et
  1-0 / 0-1 amortis. À recalibrer sur un historique réel avant de changer le signe.
- Les tips 1X2 / DC / OU2.5 issus du marché ne passent PAS par CALIBRATION.
- CODE_FILET (OV_0.5) n’est jamais un tip classé ; il sert de plan B affiché.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np

# Correction Dixon–Coles des petits scores (voir docstring module).
RHO = -0.06
VERSION_MOTEUR = '1.0.1'
# Part des buts attendus attribuée à la 1re mi-temps (approx. empirique).
FACTEUR_MI_TEMPS = 0.45
# Residu (sqrt SSE) au-delà duquel l’ajustement λ est jugé douteux.
RESIDU_DOUTEUX = 0.02
# Au-delà, un 1X2 favori n’est pas proposé en tip (trop « collé »).
P_1X2_MAX_RECO = 0.62
# Bornes de cotes acceptées en entrée (évite crash / λ absurdes).
COTE_MIN, COTE_MAX = 1.01, 100.0
MARGE_MAX = 0.35  # overround 1X2 au-delà → analyse refusée

# Tables empiriques (p prédite → p calibrée). Familles hors table : identité.
CALIBRATION = {
    'Total buts':        [(.233, .243), (.551, .550), (.651, .649),
                          (.752, .735), (.852, .838), (.936, .922)],
    'Mi-temps':          [(.318, .320), (.550, .547), (.652, .669),
                          (.741, .722), (.828, .778)],
    'Handicap':          [(.169, .158), (.549, .527), (.650, .614),
                          (.754, .704), (.854, .839), (.951, .939)],
    'BTTS':              [(.416, .461), (.547, .527), (.639, .562), (.731, .601)],
    'Une équipe marque': [(.417, .572), (.555, .622), (.653, .690),
                          (.749, .779), (.846, .848), (.931, .914)],
}

FAMILLES_ELIGIBLES = frozenset({
    'Total buts', 'Mi-temps', 'Handicap', 'Double chance', '1X2',
})
# Affichées en détail / jauges, jamais choisies comme tips classés.
FAMILLES_PEU_FIABLES = frozenset({
    'BTTS', 'Une équipe marque',
})
CODE_FILET = 'OV_0.5'

# Intervalles [lo, hi) sauf audacieuse inclusive à droite pour garder ~28–50,5 %.
BANDES = {
    'prudente': (0.70, 0.90),
    'equilibree': (0.55, 0.70),
    'audacieuse': (0.28, 0.505),
}


class AnalyseInvalide(ValueError):
    """Cotes ou marché incohérents : le moteur refuse de produire des tips."""


def _valider_cote(c: float, label: str) -> float:
    try:
        v = float(c)
    except (TypeError, ValueError) as e:
        raise AnalyseInvalide(f'Cote {label} non numérique.') from e
    if not math.isfinite(v) or v < COTE_MIN or v > COTE_MAX:
        raise AnalyseInvalide(
            f'Cote {label} hors bornes [{COTE_MIN}, {COTE_MAX}] : {c!r}'
        )
    return v


def devig_puissance(cotes):
    """Retire la marge d'un marché à 3 issues (méthode puissance / Shin soft).

    Préserver mieux le skew des gros favoris qu’un de-vig proportionnel simple.
    """
    inv = [1 / c for c in cotes]
    lo, hi = 1.0, 4.0
    for _ in range(90):
        k = (lo + hi) / 2
        if sum(x ** k for x in inv) > 1:
            lo = k
        else:
            hi = k
    p = [x ** ((lo + hi) / 2) for x in inv]
    s = sum(p)
    return [x / s for x in p]


def _pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _tau(x, y, lh, la, rho):
    """Facteur Dixon–Coles ; borné à > 0 pour garder une matrice valide."""
    if x == 0 and y == 0:
        t = 1 - lh * la * rho
    elif x == 0 and y == 1:
        t = 1 + lh * rho
    elif x == 1 and y == 0:
        t = 1 + la * rho
    elif x == 1 and y == 1:
        t = 1 - rho
    else:
        return 1.0
    return max(t, 1e-6)


def matrice(lh, la, rho=RHO, n=12):
    """Loi jointe P(buts_dom=i, buts_ext=j), tronquée à n puis renormalisée."""
    m = np.array([[_tau(i, j, lh, la, rho) * _pois(i, lh) * _pois(j, la)
                   for j in range(n + 1)] for i in range(n + 1)])
    total = m.sum()
    if total <= 0 or not np.isfinite(total):
        raise AnalyseInvalide('Matrice de scores dégénérée.')
    return m / total


def ajuster(p1, pn, p2, p_over25=None):
    """Retrouve λ_h, λ_a en calant P(1/N/2) (et optionnellement P(over 2.5))."""
    from scipy.optimize import minimize

    def erreur(v):
        lh, la = math.exp(v[0]), math.exp(v[1])
        M = matrice(lh, la)
        n = M.shape[0]
        i = np.arange(n)[:, None]
        j = np.arange(n)[None, :]
        q1, qn, q2 = M[i > j].sum(), np.trace(M), M[i < j].sum()
        e = (q1 - p1) ** 2 + (qn - pn) ** 2 + (q2 - p2) ** 2
        if p_over25 is not None:
            e += (M[(i + j) > 2.5].sum() - p_over25) ** 2
        return e

    r = minimize(
        erreur, [math.log(1.4), math.log(1.2)], method='Nelder-Mead',
        options={'xatol': 1e-7, 'fatol': 1e-13, 'maxiter': 6000},
    )
    lh, la = math.exp(r.x[0]), math.exp(r.x[1])
    residu = math.sqrt(max(float(r.fun), 0.0))
    # Échec d’optimiseur → résidu artificiellement élevé (flag douteuse).
    if not getattr(r, 'success', True):
        residu = max(residu, RESIDU_DOUTEUX * 2)
    return lh, la, residu


def corriger(p, famille):
    t = CALIBRATION.get(famille)
    if not t:
        return p
    xs = [a for a, _ in t]
    ys = [b for _, b in t]
    return float(np.clip(np.interp(p, xs, ys), 0.005, 0.995))


def _p_over_two_way(over, under):
    """De-vig proportionnel 2 voies (moins riche que la puissance 3 voies)."""
    return (1 / over) / (1 / over + 1 / under)


def profil_match(p1, p2):
    if max(p1, p2) >= 0.55:
        return 'desequilibre'
    if abs(p1 - p2) <= 0.08:
        return 'equilibre'
    return 'moyen'


def score_probable(M):
    """Mode de la matrice (score le plus probable), pas un score « utile » tip."""
    i, j = np.unravel_index(int(np.argmax(M)), M.shape)
    return f'{int(i)}-{int(j)}'


def libelle(code, nom_dom='Domicile', nom_ext='Extérieur'):
    table = {
        '1X2_1': f'{nom_dom} gagne',
        '1X2_N': 'Match nul',
        '1X2_2': f'{nom_ext} gagne',
        'DC_1X': f'{nom_dom} ne perd pas',
        'DC_X2': f'{nom_ext} ne perd pas',
        'DC_12': 'Pas de nul',
        'OV_0.5': 'Au moins 1 but',
        'OV_1.5': 'Au moins 2 buts',
        'OV_2.5': 'Plus de 2,5 buts',
        'OV_3.5': 'Plus de 3,5 buts',
        'OV_4.5': 'Plus de 4,5 buts',
        'UN_0.5': 'Aucun but',
        'UN_2.5': 'Moins de 2,5 buts',
        'UN_3.5': 'Moins de 3,5 buts',
        'UN_4.5': 'Moins de 4,5 buts',
        'MRG_H_2': f'{nom_dom} gagne par 2 buts ou plus',
        'MRG_H_3': f'{nom_dom} gagne par 3 buts ou plus',
        'MRG_A_2': f'{nom_ext} gagne par 2 buts ou plus',
        'MRG_A_3': f'{nom_ext} gagne par 3 buts ou plus',
        'HCP_H_+1': f'{nom_dom} ne perd pas de plus d’un but',
        'HCP_A_+1': f'{nom_ext} ne perd pas de plus d’un but',
        'HT_1': f'{nom_dom} mène à la pause',
        'HT_N': 'Nul à la pause',
        'HT_2': f'{nom_ext} mène à la pause',
        'HT_OV_0.5': 'Au moins 1 but avant la pause',
        'HT_OV_1.5': 'Au moins 2 buts avant la pause',
        'HT_UN_0.5': 'Aucun but avant la pause',
        'HT_UN_1.5': 'Moins de 1,5 but avant la pause',
        'BTTS_O': 'Les deux équipes marquent',
        'BTTS_N': 'Au moins une équipe ne marque pas',
        'DOM_MARQUE': f'{nom_dom} marque',
        'EXT_MARQUE': f'{nom_ext} marque',
    }
    return table.get(code, code)


def _option(code, famille, p, origine, nom_dom, nom_ext, corriger_p=True):
    if origine == 'calcul' and corriger_p:
        p = corriger(p, famille)
    p = float(np.clip(p, 0.005, 0.995))
    return {
        'code': code,
        'famille': famille,
        'libelle': libelle(code, nom_dom, nom_ext),
        'probabilite': p,
        'cote_juste': 1.0 / p,
        'origine': origine,
        'niveau': 'detail',
    }


def options_depuis_matrice(lh, la, p1, pn, p2, p_over25, nom_dom, nom_ext):
    """Construit toutes les options. 1X2 et OU 2,5 viennent du marché, non corrigés."""
    M = matrice(lh, la)
    n = M.shape[0]
    i = np.arange(n)[:, None]
    j = np.arange(n)[None, :]
    tot, ecart = i + j, i - j

    Mh = matrice(FACTEUR_MI_TEMPS * lh, FACTEUR_MI_TEMPS * la)
    nh = Mh.shape[0]
    ih = np.arange(nh)[:, None]
    jh = np.arange(nh)[None, :]
    htot, hecart = ih + jh, ih - jh

    opts = []
    add = opts.append

    add(_option('1X2_1', '1X2', p1, 'marche', nom_dom, nom_ext, corriger_p=False))
    add(_option('1X2_N', '1X2', pn, 'marche', nom_dom, nom_ext, corriger_p=False))
    add(_option('1X2_2', '1X2', p2, 'marche', nom_dom, nom_ext, corriger_p=False))

    add(_option('DC_1X', 'Double chance', p1 + pn, 'marche', nom_dom, nom_ext, False))
    add(_option('DC_X2', 'Double chance', pn + p2, 'marche', nom_dom, nom_ext, False))
    add(_option('DC_12', 'Double chance', p1 + p2, 'marche', nom_dom, nom_ext, False))

    if p_over25 is not None:
        add(_option('OV_2.5', 'Total buts', p_over25, 'marche', nom_dom, nom_ext, False))
        add(_option('UN_2.5', 'Total buts', 1 - p_over25, 'marche', nom_dom, nom_ext, False))
    else:
        add(_option('OV_2.5', 'Total buts', float(M[tot > 2.5].sum()), 'calcul', nom_dom, nom_ext))
        add(_option('UN_2.5', 'Total buts', float(M[tot < 2.5].sum()), 'calcul', nom_dom, nom_ext))

    for seuil in (0.5, 1.5, 3.5, 4.5):
        add(_option(f'OV_{seuil}', 'Total buts', float(M[tot > seuil].sum()),
                    'calcul', nom_dom, nom_ext))
        add(_option(f'UN_{seuil}', 'Total buts', float(M[tot < seuil].sum()),
                    'calcul', nom_dom, nom_ext))

    for n_mrg in (2, 3):
        add(_option(f'MRG_H_{n_mrg}', 'Handicap', float(M[ecart >= n_mrg].sum()),
                    'calcul', nom_dom, nom_ext))
        add(_option(f'MRG_A_{n_mrg}', 'Handicap', float(M[-ecart >= n_mrg].sum()),
                    'calcul', nom_dom, nom_ext))

    add(_option('HCP_H_+1', 'Handicap', float(M[ecart + 1 >= 0].sum()),
                'calcul', nom_dom, nom_ext))
    add(_option('HCP_A_+1', 'Handicap', float(M[-ecart + 1 >= 0].sum()),
                'calcul', nom_dom, nom_ext))

    add(_option('HT_1', 'Mi-temps', float(Mh[hecart > 0].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('HT_N', 'Mi-temps', float(Mh[hecart == 0].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('HT_2', 'Mi-temps', float(Mh[hecart < 0].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('HT_OV_0.5', 'Mi-temps', float(Mh[htot > 0.5].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('HT_OV_1.5', 'Mi-temps', float(Mh[htot > 1.5].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('HT_UN_0.5', 'Mi-temps', float(Mh[htot < 0.5].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('HT_UN_1.5', 'Mi-temps', float(Mh[htot < 1.5].sum()), 'calcul', nom_dom, nom_ext))

    add(_option('BTTS_O', 'BTTS', float(M[(i > 0) & (j > 0)].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('BTTS_N', 'BTTS', float(M[~((i > 0) & (j > 0))].sum()), 'calcul', nom_dom, nom_ext))
    add(_option('DOM_MARQUE', 'Une équipe marque', float(M[1:, :].sum()),
                'calcul', nom_dom, nom_ext))
    add(_option('EXT_MARQUE', 'Une équipe marque', float(M[:, 1:].sum()),
                'calcul', nom_dom, nom_ext))

    return opts, M


def analyser(cotes_1x2, cotes_ou25=None, nom_dom='Domicile', nom_ext='Extérieur'):
    """Analyse un match à partir des cotes.

    cotes_1x2 = (c1, cn, c2) ; cotes_ou25 = (over, under) facultatif.
    Lève AnalyseInvalide si les cotes sont inutilisables.
    """
    c1 = _valider_cote(cotes_1x2[0], '1')
    cn = _valider_cote(cotes_1x2[1], 'N')
    c2 = _valider_cote(cotes_1x2[2], '2')
    p1, pn, p2 = devig_puissance([c1, cn, c2])
    marge = 1 / c1 + 1 / cn + 1 / c2 - 1
    if marge < 0 or marge > MARGE_MAX:
        raise AnalyseInvalide(f'Marge 1X2 hors bornes : {marge:.3f}')

    p_over25 = None
    if cotes_ou25:
        o = _valider_cote(cotes_ou25[0], 'OU over')
        u = _valider_cote(cotes_ou25[1], 'OU under')
        p_over25 = _p_over_two_way(o, u)

    lh, la, residu = ajuster(p1, pn, p2, p_over25)
    opts, M = options_depuis_matrice(lh, la, p1, pn, p2, p_over25, nom_dom, nom_ext)
    return {
        'buts_dom_attendus': lh,
        'buts_ext_attendus': la,
        'p1': p1,
        'pn': pn,
        'p2': p2,
        'p_over25': p_over25,
        'score_probable': score_probable(M),
        'profil': profil_match(p1, p2),
        'marge_marche': marge,
        'residu': residu,
        'douteuse': residu > RESIDU_DOUTEUX,
        'version_moteur': VERSION_MOTEUR,
        'options': opts,
    }


def est_eligible(opt):
    if opt['code'] == CODE_FILET:
        return False
    if opt['famille'] in FAMILLES_PEU_FIABLES:
        return False
    if opt['famille'] not in FAMILLES_ELIGIBLES:
        return False
    if opt['famille'] == '1X2' and opt['probabilite'] >= P_1X2_MAX_RECO:
        return False
    return True


def _dans_bande(p, niveau):
    lo, hi = BANDES[niveau]
    return lo <= p < hi if niveau != 'audacieuse' else lo <= p <= hi


def _bonus_profil(opt, profil):
    fam = opt['famille']
    if profil == 'desequilibre' and fam == 'Handicap':
        return 0.18
    if profil == 'equilibre' and fam in ('Double chance', 'Total buts'):
        return 0.18
    if profil == 'moyen' and fam in ('Total buts', 'Mi-temps'):
        return 0.06
    return 0.0


def _score_choix(opt, profil, moyennes):
    """Préfère les tips qui s’écartent de la moyenne journée + bonus de profil."""
    p = opt['probabilite']
    moy = moyennes.get(opt['code'], p)
    return abs(p - moy) + _bonus_profil(opt, profil)


def choisir_trois(options, profil, moyennes, codes_eviter=None):
    """Retourne une copie des options avec niveau renseigné (3 + filet).

    codes_eviter : codes sur-représentés sur la journée — évités si une
    alternative éligible existe dans la bande (sinon repli autorisé).
    """
    eviter = set(codes_eviter or ())
    out = [dict(o) for o in options]
    # Remet les niveaux au détail sauf filet (re-classement propre).
    for o in out:
        o['niveau'] = 'filet' if o['code'] == CODE_FILET else 'detail'

    familles_prises = set()
    codes_pris = set()

    def _candidats(niveau, ignorer_eviter=False):
        bande = [
            o for o in out
            if est_eligible(o)
            and o['code'] not in codes_pris
            and o['famille'] not in familles_prises
            and _dans_bande(o['probabilite'], niveau)
            and (ignorer_eviter or o['code'] not in eviter)
        ]
        if bande:
            bande.sort(key=lambda o: -_score_choix(o, profil, moyennes))
            return bande
        centre = (BANDES[niveau][0] + BANDES[niveau][1]) / 2
        repli = [
            o for o in out
            if est_eligible(o)
            and o['code'] not in codes_pris
            and o['famille'] not in familles_prises
            and (ignorer_eviter or o['code'] not in eviter)
        ]
        repli.sort(
            key=lambda o: abs(o['probabilite'] - centre) - _score_choix(o, profil, moyennes)
        )
        return repli

    for niveau in ('prudente', 'equilibree', 'audacieuse'):
        candidats = _candidats(niveau, ignorer_eviter=False)
        if not candidats and eviter:
            candidats = _candidats(niveau, ignorer_eviter=True)
        if not candidats:
            continue
        choisi = candidats[0]
        choisi['niveau'] = niveau
        familles_prises.add(choisi['famille'])
        codes_pris.add(choisi['code'])

    return out


def moyennes_par_code(listes_options):
    acc = defaultdict(list)
    for opts in listes_options:
        for o in opts:
            acc[o['code']].append(o['probabilite'])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def classer_journee(analyses):
    """Ajoute le classement (niveaux) à chaque analyse, en tenant compte de la journée.

    Si une même tip occupe trop souvent le même niveau, un 2e passage évite
    ces codes lorsqu’une alternative existe (anti-uniformité douce).
    """
    moy = moyennes_par_code(a['options'] for a in analyses)
    for a in analyses:
        a['options'] = choisir_trois(a['options'], a['profil'], moy)

    sels = [selections_niveaux(a['options']) for a in analyses]
    exclus = set()
    if len(sels) >= 3 and uniformite_excessive(sels):
        for niveau in ('prudente', 'equilibree', 'audacieuse'):
            codes = [s.get(niveau) for s in sels if s.get(niveau)]
            if not codes:
                continue
            code_dom, count = Counter(codes).most_common(1)[0]
            if count > len(sels) / 3:
                exclus.add(code_dom)
    if exclus:
        for a in analyses:
            a['options'] = choisir_trois(a['options'], a['profil'], moy, codes_eviter=exclus)
            a['uniformite_corrigee'] = True
    else:
        for a in analyses:
            a['uniformite_corrigee'] = False
    return analyses


def uniformite_excessive(selections, seuil=1 / 3):
    """True si une même option occupe le même niveau sur plus d'un tiers des matchs.

    selections : liste de dicts {niveau: code} pour prudente/equilibree/audacieuse.
    """
    if not selections:
        return False
    n = len(selections)
    for niveau in ('prudente', 'equilibree', 'audacieuse'):
        codes = [s.get(niveau) for s in selections if s.get(niveau)]
        if not codes:
            continue
        _, count = Counter(codes).most_common(1)[0]
        if count > n * seuil:
            return True
    return False


def selections_niveaux(options):
    return {o['niveau']: o['code'] for o in options if o['niveau'] in BANDES}
