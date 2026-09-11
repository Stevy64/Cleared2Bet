"""Helpers fiches / logos clubs (sans exposer les fournisseurs à l’UI)."""
from __future__ import annotations

from typing import Any

from django.db.models import Q

from paris.models import Equipe, Match


def logo_url_pour(eq: Equipe) -> str:
    url = (eq.logo_externe or '').strip()
    if url:
        return url
    if eq.sofascore_id:
        return f'https://img.sofascore.com/api/v1/team/{int(eq.sofascore_id)}/image'
    return ''


def infos_equipe_locale(eq: Equipe) -> dict[str, Any]:
    """Forme / récents depuis les matchs terminés en base."""
    matchs = (
        Match.objects
        .filter(Q(domicile=eq) | Q(exterieur=eq), statut='termine')
        .filter(buts_dom__isnull=False, buts_ext__isnull=False)
        .select_related('domicile', 'exterieur', 'competition')
        .order_by('-coup_denvoi')[:8]
    )
    recents = []
    forme: list[str] = []
    for m in matchs:
        is_home = m.domicile_id == eq.id
        hs, aw = int(m.buts_dom), int(m.buts_ext)
        if is_home:
            res = 'W' if hs > aw else ('L' if hs < aw else 'D')
            adversaire = m.exterieur.nom_court or m.exterieur.nom
        else:
            res = 'W' if aw > hs else ('L' if aw < hs else 'D')
            adversaire = m.domicile.nom_court or m.domicile.nom
        forme.append(res)
        recents.append({
            'adversaire': adversaire,
            'score': f'{hs}-{aw}',
            'domicile': is_home,
            'resultat': res,
            'coup_denvoi': m.coup_denvoi.isoformat() if m.coup_denvoi else None,
        })
    forme_chrono = list(reversed(forme[:5]))
    pays = None
    m_ref = (
        Match.objects.filter(Q(domicile=eq) | Q(exterieur=eq))
        .select_related('competition')
        .order_by('-coup_denvoi')
        .first()
    )
    if m_ref and m_ref.competition_id:
        pays = m_ref.competition.pays or None
    return {
        'id': eq.sofascore_id or eq.thesportsdb_id,
        'nom': eq.nom,
        'nom_court': eq.nom_court,
        'pays': pays,
        'forme': forme_chrono,
        'position': None,
        'note_moyenne': None,
        'classement': None,
        'recents': recents,
    }


def enrichir_equipe_pour_snapshot(eq: Equipe, *, resoudre_externe: bool = True) -> dict[str, Any]:
    """Prépare le bloc équipe du snapshot (logo CDN + fiche)."""
    logo = logo_url_pour(eq)
    fiche = dict(eq.fiche_club or {})
    if not fiche.get('recents') and not fiche.get('forme'):
        fiche = infos_equipe_locale(eq)

    tid = eq.thesportsdb_id
    if resoudre_externe and (not tid or not logo or not fiche.get('forme')):
        try:
            from paris import thesportsdb as tsdb
            if not tid:
                tid = tsdb.resoudre_id(eq.nom, eq.nom_court)
            if tid:
                try:
                    data = tsdb.infos_equipe(tid)
                    badge = (data.get('badge_url') or '').strip()
                    if badge:
                        logo = badge
                    if data.get('forme') or data.get('recents'):
                        # Merge : externe prioritaire si plus riche
                        if len(data.get('recents') or []) >= len(fiche.get('recents') or []):
                            fiche = {
                                k: data.get(k) for k in (
                                    'nom', 'nom_court', 'pays', 'forme', 'position',
                                    'classement', 'recents', 'note_moyenne',
                                )
                                if data.get(k) is not None
                            }
                            fiche['nom'] = eq.nom
                            fiche['nom_court'] = eq.nom_court
                except tsdb.SportsDbErreur:
                    pass
        except Exception:  # noqa: BLE001
            pass

    if not logo and eq.sofascore_id:
        logo = f'https://img.sofascore.com/api/v1/team/{int(eq.sofascore_id)}/image'

    fiche.pop('source', None)
    fiche.pop('badge_url', None)

    return {
        'nom': eq.nom,
        'nom_court': eq.nom_court,
        'slug': eq.slug,
        'sofascore_id': eq.sofascore_id,
        'thesportsdb_id': tid or eq.thesportsdb_id,
        'logo_externe': logo,
        'fiche_club': fiche,
    }
