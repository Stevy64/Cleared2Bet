"""Snapshot matchs + cotes + analyses pour déploiement hors sync live (ex. PythonAnywhere)."""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_datetime

from paris.models import Analyse, Competition, Contexte, Cote, Equipe, Match, Option

SNAPSHOT_VERSION = 1


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _dec(v) -> float | None:
    if v is None:
        return None
    return float(v)


def exporter_snapshot(*, jours: int | None = None) -> dict[str, Any]:
    """Exporte les matchs « réels » (avec sofascore_id) + dépendances."""
    qs = (
        Match.objects
        .filter(sofascore_id__isnull=False)
        .select_related('competition', 'domicile', 'exterieur', 'analyse', 'contexte')
        .prefetch_related('cotes', 'analyse__options')
        .order_by('coup_denvoi')
    )
    if jours is not None and jours > 0:
        from datetime import timedelta
        from django.utils import timezone
        debut = timezone.now() - timedelta(days=jours)
        fin = timezone.now() + timedelta(days=jours)
        qs = qs.filter(coup_denvoi__gte=debut, coup_denvoi__lte=fin)

    matchs = list(qs)
    comp_ids = {m.competition_id for m in matchs}
    eq_ids = {m.domicile_id for m in matchs} | {m.exterieur_id for m in matchs}

    competitions = [
        {
            'code': c.code,
            'nom': c.nom,
            'pays': c.pays,
            'ordre': c.ordre,
            'actif': c.actif,
            'sofascore_id': c.sofascore_id,
        }
        for c in Competition.objects.filter(pk__in=comp_ids).order_by('ordre', 'code')
    ]
    equipes = [
        {
            'nom': e.nom,
            'nom_court': e.nom_court,
            'slug': e.slug,
            'sofascore_id': e.sofascore_id,
            'thesportsdb_id': e.thesportsdb_id,
        }
        for e in Equipe.objects.filter(pk__in=eq_ids).order_by('slug')
    ]

    out_matchs = []
    for m in matchs:
        bloc: dict[str, Any] = {
            'sofascore_id': m.sofascore_id,
            'competition_code': m.competition.code,
            'domicile_slug': m.domicile.slug,
            'exterieur_slug': m.exterieur.slug,
            'coup_denvoi': _iso(m.coup_denvoi),
            'journee': m.journee,
            'statut': m.statut,
            'buts_dom': m.buts_dom,
            'buts_ext': m.buts_ext,
            'buts_dom_mt': m.buts_dom_mt,
            'buts_ext_mt': m.buts_ext_mt,
            'cotes': [
                {
                    'bookmaker': c.bookmaker,
                    'marche': c.marche,
                    'selection': c.selection,
                    'valeur': _dec(c.valeur),
                    'nb_sources': c.nb_sources,
                    'releve_le': _iso(c.releve_le),
                }
                for c in m.cotes.all()
            ],
            'contexte': None,
            'analyse': None,
        }
        try:
            ctx = m.contexte
            bloc['contexte'] = {
                'forme_dom': ctx.forme_dom,
                'forme_ext': ctx.forme_ext,
                'absents_dom': ctx.absents_dom,
                'absents_ext': ctx.absents_ext,
                'tendance_buts': ctx.tendance_buts,
                'a_savoir': ctx.a_savoir,
                'confrontations': ctx.confrontations,
                'fiabilite': ctx.fiabilite,
            }
        except Contexte.DoesNotExist:
            pass
        try:
            a = m.analyse
            bloc['analyse'] = {
                'buts_dom_attendus': a.buts_dom_attendus,
                'buts_ext_attendus': a.buts_ext_attendus,
                'p1': a.p1,
                'pn': a.pn,
                'p2': a.p2,
                'score_probable': a.score_probable,
                'profil': a.profil,
                'marge_marche': a.marge_marche,
                'residu': a.residu,
                'version_moteur': a.version_moteur,
                'options': [
                    {
                        'famille': o.famille,
                        'code': o.code,
                        'libelle': o.libelle,
                        'probabilite': o.probabilite,
                        'cote_juste': o.cote_juste,
                        'niveau': o.niveau,
                        'origine': o.origine,
                        'resultat': o.resultat,
                    }
                    for o in a.options.all()
                ],
            }
        except Analyse.DoesNotExist:
            pass
        out_matchs.append(bloc)

    return {
        'version': SNAPSHOT_VERSION,
        'exporte_le': datetime.now(dt_timezone.utc).isoformat(),
        'competitions': competitions,
        'equipes': equipes,
        'matchs': out_matchs,
    }


@transaction.atomic
def importer_snapshot(data: dict[str, Any]) -> dict[str, int]:
    """Upsert snapshot (compétitions, équipes, matchs, cotes, analyses)."""
    if not isinstance(data, dict) or 'matchs' not in data:
        raise ValueError('Snapshot invalide : clé "matchs" manquante.')

    stats = {
        'competitions': 0,
        'equipes': 0,
        'matchs': 0,
        'cotes': 0,
        'analyses': 0,
        'options': 0,
        'contextes': 0,
    }

    for c in data.get('competitions') or []:
        Competition.objects.update_or_create(
            code=c['code'],
            defaults={
                'nom': c.get('nom') or c['code'],
                'pays': c.get('pays') or '',
                'ordre': c.get('ordre', 100),
                'actif': c.get('actif', True),
                'sofascore_id': c.get('sofascore_id'),
            },
        )
        stats['competitions'] += 1

    for e in data.get('equipes') or []:
        sid = e.get('sofascore_id')
        defaults = {
            'nom': e['nom'],
            'nom_court': e.get('nom_court') or e['nom'][:24],
            'slug': e['slug'],
            'thesportsdb_id': e.get('thesportsdb_id'),
        }
        if sid:
            eq = Equipe.objects.filter(sofascore_id=sid).first()
            if eq:
                for k, v in defaults.items():
                    setattr(eq, k, v)
                eq.sofascore_id = sid
                eq.save()
            else:
                Equipe.objects.update_or_create(
                    slug=e['slug'],
                    defaults={**defaults, 'sofascore_id': sid},
                )
        else:
            Equipe.objects.update_or_create(slug=e['slug'], defaults=defaults)
        stats['equipes'] += 1

    for m in data.get('matchs') or []:
        sid = m.get('sofascore_id')
        if not sid:
            continue
        competition = Competition.objects.get(code=m['competition_code'])
        domicile = Equipe.objects.get(slug=m['domicile_slug'])
        exterieur = Equipe.objects.get(slug=m['exterieur_slug'])
        coup = parse_datetime(m['coup_denvoi'])
        if coup is None:
            continue

        match, _ = Match.objects.update_or_create(
            sofascore_id=sid,
            defaults={
                'competition': competition,
                'domicile': domicile,
                'exterieur': exterieur,
                'coup_denvoi': coup,
                'journee': m.get('journee') or '',
                'statut': m.get('statut') or 'a_venir',
                'buts_dom': m.get('buts_dom'),
                'buts_ext': m.get('buts_ext'),
                'buts_dom_mt': m.get('buts_dom_mt'),
                'buts_ext_mt': m.get('buts_ext_mt'),
            },
        )
        stats['matchs'] += 1

        # Remplace les cotes exportées (évite les doublons)
        if m.get('cotes') is not None:
            match.cotes.all().delete()
            for c in m['cotes']:
                releve = parse_datetime(c.get('releve_le') or '') or coup
                Cote.objects.create(
                    match=match,
                    bookmaker=c.get('bookmaker') or 'snapshot',
                    marche=c['marche'],
                    selection=c['selection'],
                    valeur=Decimal(str(c['valeur'])),
                    nb_sources=c.get('nb_sources') or 1,
                    releve_le=releve,
                )
                stats['cotes'] += 1

        ctx = m.get('contexte')
        if ctx:
            Contexte.objects.update_or_create(
                match=match,
                defaults={
                    'forme_dom': ctx.get('forme_dom') or '',
                    'forme_ext': ctx.get('forme_ext') or '',
                    'absents_dom': ctx.get('absents_dom') or '',
                    'absents_ext': ctx.get('absents_ext') or '',
                    'tendance_buts': ctx.get('tendance_buts') or '',
                    'a_savoir': ctx.get('a_savoir') or '',
                    'confrontations': ctx.get('confrontations') or '',
                    'fiabilite': ctx.get('fiabilite') or 'moyenne',
                    'source': '',
                },
            )
            stats['contextes'] += 1

        ana = m.get('analyse')
        if ana:
            analyse, _ = Analyse.objects.update_or_create(
                match=match,
                defaults={
                    'buts_dom_attendus': ana['buts_dom_attendus'],
                    'buts_ext_attendus': ana['buts_ext_attendus'],
                    'p1': ana['p1'],
                    'pn': ana['pn'],
                    'p2': ana['p2'],
                    'score_probable': ana.get('score_probable') or '',
                    'profil': ana.get('profil') or 'moyen',
                    'marge_marche': ana.get('marge_marche') or 0,
                    'residu': ana.get('residu') or 0,
                    'version_moteur': ana.get('version_moteur') or '3.1.0',
                },
            )
            stats['analyses'] += 1
            analyse.options.all().delete()
            for o in ana.get('options') or []:
                Option.objects.create(
                    analyse=analyse,
                    famille=o['famille'],
                    code=o['code'],
                    libelle=o['libelle'],
                    probabilite=o['probabilite'],
                    cote_juste=o['cote_juste'],
                    niveau=o.get('niveau') or 'detail',
                    origine=o.get('origine') or 'calcul',
                    resultat=o.get('resultat') or 'attente',
                )
                stats['options'] += 1

    return stats
