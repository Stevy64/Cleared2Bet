"""Justifications terrain — ton footeux, populaire, détendu (sans maths)."""
from __future__ import annotations

from typing import Any


def _pct(p: float | None) -> str:
    if p is None:
        return '—'
    return f'{round(float(p) * 100)} %'


def _txt(val: Any) -> str:
    return (str(val) if val is not None else '').strip()


def _phrase(s: str) -> str:
    s = _txt(s)
    if not s:
        return ''
    return s if s.endswith(('.', '!', '?')) else s + '.'


def _niv_label(niveau: str) -> str:
    return {
        'prudente': 'Prudente',
        'filet': 'Filet de sécurité',
        'equilibree': 'Équilibrée',
        'audacieuse': 'Audacieuse',
    }.get(niveau, niveau or 'Tip')


def _arg(cle: str, titre: str, texte: str, icon: str) -> dict[str, str] | None:
    texte = _phrase(texte)
    if not texte:
        return None
    return {'cle': cle, 'titre': titre, 'texte': texte, 'icon': icon}


def _accroche_terrain(
    *,
    libelle: str,
    niveau: str,
    p: float | None,
    domicile: str,
    exterieur: str,
) -> str:
    duo = f'{domicile} – {exterieur}'.strip(' –')
    conf = _pct(p)
    if niveau == 'filet':
        return (
            f'Sur {duo or "ce match"}, « {libelle} » ({conf}) : le joker du banc. '
            f'Si le tip principal rate le cadre, celui-là est là pour rattraper le coup.'
        )
    if niveau == 'prudente':
        return (
            f'On part sur « {libelle} » ({conf}). Pas le coup de génie du vestiaire — '
            f'juste le scénario propre, celui que tu joues sans te ronger les ongles.'
        )
    return (
        f'Sur {duo or "ce match"}, Cleared2Bet retient « {libelle} » ({conf}). '
        f'Lecture terrain, pas de blabla de plateau TV.'
    )


def _lecture_profil(analyse: Any | None, domicile: str, exterieur: str) -> str:
    if analyse is None:
        return ''
    profil = getattr(analyse, 'profil', '') or ''
    score = _txt(getattr(analyse, 'score_probable', ''))
    if profil == 'desequilibre':
        base = (
            f'Y’a un gros favori dans l’air ({domicile or "domicile"} vs '
            f'{exterieur or "extérieur"}). Un camp devrait tenir le ballon et le rythme.'
        )
    elif profil == 'equilibre':
        base = (
            'Match serré au feeling : peu d’écart sur le papier. '
            'Forme, absents et intensité peuvent tout faire basculer.'
        )
    elif profil == 'moyen':
        base = (
            f'{domicile or "L’équipe à domicile"} part un cran devant, '
            'sans que ce soit déjà plié au coup d’envoi.'
        )
    else:
        base = ''
    if score:
        base = (base + ' ' if base else '') + f'Score qui colle bien : autour de {score}.'
    return base


def _assaisonner_forme(texte: str) -> str:
    t = _txt(texte)
    if not t:
        return ''
    low = t.lower()
    if 'bonne dynamique' in low:
        return t.rstrip('.') + ' — ils arrivent chauds, faut en profiter.'
    if 'série compliquée' in low:
        return t.rstrip('.') + ' — là, attendre un festival de buts serait un peu optimiste.'
    return t


def _assaisonner_h2h(texte: str) -> str:
    t = _txt(texte)
    if not t:
        return ''
    low = t.lower()
    if 'dominé' in low:
        return t.rstrip('.') + ' L’historique parle assez fort, non ?'
    if 'dessus' in low:
        return t.rstrip('.') + ' Souvent le même scénario dans ce duel…'
    if 'serré' in low or 'nul' in low:
        return t.rstrip('.') + ' Bref : pas le soir pour jouer les héros.'
    return t.rstrip('.') + ' Ça donne le climat du match avant même le coup d’envoi.'


def _assaisonner_absents(texte: str) -> str:
    t = _txt(texte)
    if not t:
        return ''
    return t.rstrip('.') + ' — un forfait, et parfois le match change de visage.'


def _assaisonner_meteo(texte: str) -> str:
    t = _txt(texte)
    if not t:
        return ''
    low = t.lower()
    if any(k in low for k in ('pluie', 'orage', 'neige', 'brouillard')):
        return t.rstrip('.') + ' Terrain lourd : souvent moins de folie devant le but.'
    if any(k in low for k in ('ensoleillé', 'dégagé')):
        return t.rstrip('.') + ' Beau ciel : les jambes n’ont plus d’excuse.'
    return t


def _lien_tip_contexte(
    *,
    libelle: str,
    famille: str,
    niveau: str,
    contexte: Any | None,
) -> str:
    """Relie le tip au contexte match — ton footeux, pas savant."""
    lib = (libelle or '').lower()
    fam = (famille or '').lower()
    tendance = _txt(getattr(contexte, 'tendance_buts', None) if contexte else '')
    h2h = _txt(getattr(contexte, 'confrontations', None) if contexte else '')

    if 'but' in lib or 'total' in fam:
        if tendance:
            return (
                tendance.rstrip('.')
                + f' Du coup « {libelle or "ce tip"} » tombe plutôt bien.'
            )
        if any(k in h2h.lower() for k in ('serré', 'nul', 'équilibr')):
            return (
                'Les derniers duels, c’était plutôt sage devant le but. '
                f'« {libelle} » colle à cette vibe.'
            )
        return (
            f'« {libelle} » : le scénario buts le plus clean. '
            'Pas besoin d’imaginer un 5-4 de folie.'
        )
    if 'ne perd pas' in lib or 'double' in fam:
        return (
            f'« {libelle} » : tu couvres le réaliste sans exiger le carton plein. '
            'Pratique quand le match peut basculer sur un détail.'
        )
    if niveau == 'filet':
        return (
            'Le filet vise un truc qui tombe souvent (genre « au moins un but »). '
            'C’est la sécurité du jour, pas le highlight Instagram.'
        )
    return (
        f'« {libelle} » résume la tendance du match — '
        'sans te promettre le score exact comme un oracle.'
    )


def justifier_option(
    *,
    option: Any,
    analyse: Any | None = None,
    contexte: Any | None = None,
    domicile: str = '',
    exterieur: str = '',
) -> dict[str, Any]:
    """Retourne titre, accroche et arguments terrain pour le popup compos."""
    libelle = getattr(option, 'libelle', None) or (option.get('libelle') if isinstance(option, dict) else '')
    niveau = getattr(option, 'niveau', None) or (option.get('niveau') if isinstance(option, dict) else '')
    famille = getattr(option, 'famille', None) or (option.get('famille') if isinstance(option, dict) else '')
    p = getattr(option, 'probabilite', None) if not isinstance(option, dict) else option.get('probabilite')

    niv_label = _niv_label(niveau or '')
    titre = f'{niv_label} · {libelle}'
    accroche = _accroche_terrain(
        libelle=libelle or 'ce tip',
        niveau=niveau or '',
        p=p,
        domicile=domicile,
        exterieur=exterieur,
    )

    arguments: list[dict[str, str]] = []

    def push(item: dict[str, str] | None) -> None:
        if item and len(arguments) < 5:
            if any(a['texte'] == item['texte'] for a in arguments):
                return
            arguments.append(item)

    push(_arg(
        'lecture',
        'Pourquoi ce tip',
        _lien_tip_contexte(
            libelle=libelle or '',
            famille=famille or '',
            niveau=niveau or '',
            contexte=contexte,
        ),
        'crosshair',
    ))

    if contexte is not None:
        forme_d = _assaisonner_forme(getattr(contexte, 'forme_dom', ''))
        forme_e = _assaisonner_forme(getattr(contexte, 'forme_ext', ''))
        if forme_d and forme_e:
            push(_arg(
                'forme',
                'Formes récentes',
                f'{forme_d.rstrip(".")}. {forme_e}',
                'activity',
            ))
        else:
            push(_arg(
                'forme_dom',
                f'Forme · {domicile or "Domicile"}',
                forme_d,
                'activity',
            ))
            push(_arg(
                'forme_ext',
                f'Forme · {exterieur or "Extérieur"}',
                forme_e,
                'activity',
            ))
        push(_arg(
            'h2h',
            'Confrontations',
            _assaisonner_h2h(getattr(contexte, 'confrontations', '')),
            'swords',
        ))
        abs_d = _txt(getattr(contexte, 'absents_dom', ''))
        abs_e = _txt(getattr(contexte, 'absents_ext', ''))
        if abs_d or abs_e:
            bits = []
            if abs_d:
                bits.append(f'{domicile or "Domicile"} : {abs_d}')
            if abs_e:
                bits.append(f'{exterieur or "Extérieur"} : {abs_e}')
            push(_arg(
                'absents',
                'Absents / indisponibles',
                _assaisonner_absents(' · '.join(bits)),
                'user-x',
            ))
        push(_arg(
            'tendance',
            'Tendance du match',
            getattr(contexte, 'tendance_buts', ''),
            'trending',
        ))
        push(_arg(
            'savoir',
            'Météo & conditions',
            _assaisonner_meteo(getattr(contexte, 'a_savoir', '')),
            'cloud',
        ))

    if len(arguments) < 3:
        push(_arg(
            'profil',
            'Lecture du match',
            _lecture_profil(analyse, domicile, exterieur),
            'info',
        ))
    if niveau == 'filet' and len(arguments) < 4:
        push(_arg(
            'filet',
            'Rôle du filet',
            'Le filet, c’est le remplacant qui entre à la 70ᵉ : discret, utile, et tu es content qu’il soit là.',
            'shield',
        ))
    elif niveau == 'prudente' and len(arguments) < 4:
        push(_arg(
            'prudente',
            'Niveau Prudente',
            'On cherche le tip « je dors cool », pas le score miracle raconté au café.',
            'shield',
        ))

    if not arguments:
        push(_arg(
            'fallback',
            'Lecture Cleared2Bet',
            'Forme, duels, contexte : on a croisé le tout, et ce tip sort du lot sans forcer.',
            'info',
        ))

    points = [a['texte'] for a in arguments]

    return {
        'titre': titre,
        'accroche': accroche,
        'arguments': arguments,
        'points': points,
        'niveau': niveau,
        'probabilite': p,
        'libelle': libelle,
    }
