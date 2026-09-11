"""Synchronise matchs, cotes 1X2/OU2.5, scores et H2H depuis SofaScore.

Règle anti-blocage : **aucun appel HTTP à l’intérieur d’une transaction**.
Les cotes / le contexte sont récupérés d’abord ; seule l’écriture DB est atomic.
"""

from __future__ import annotations

from datetime import timezone as dt_tz
from typing import Any

from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.utils import timezone

from paris import sofascore as sofa
from paris.models import Competition, Contexte, Cote, Equipe, Match
from paris.reglement import regler_match


class Command(BaseCommand):
    help = (
        'Synchronise les matchs à venir / récents (cotes, scores) depuis '
        'SofaScore pour PL, LIGA, L1, SA, UCL. '
        'Les transactions DB restent courtes (pas de HTTP dedans).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--pages', type=int, default=2, help='Pages next')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--calculer',
            action='store_true',
            help='Lance calculer_analyses pour les jours touchés',
        )
        parser.add_argument(
            '--passes',
            type=int,
            default=1,
            help='Pages d’événements terminés (last) à récupérer',
        )
        parser.add_argument(
            '--contexte',
            action='store_true',
            help='Inclut H2H/forme/météo (lent : plusieurs HTTP par match)',
        )
        parser.add_argument(
            '--sans-contexte',
            action='store_true',
            help='(Deprecated, défaut) Ignore le contexte terrain',
        )

    def handle(self, *args, **opts):
        pages = opts['pages']
        dry = opts['dry_run']
        # Contexte opt-in : par défaut off pour ne jamais bloquer cron / make sync.
        avec_contexte = bool(opts['contexte']) and not opts['sans_contexte']
        n_new = n_upd = n_skip = n_regles = n_err = 0
        jours = set()

        for tid, meta in sofa.TOURNOIS.items():
            self.stdout.write(f'- {meta["code"]}...')
            self.stdout.flush()
            close_old_connections()

            events: list[dict] = []
            try:
                events.extend(sofa.evenements_suivants(tid, pages=pages))
            except sofa.SofaScoreErreur as e:
                self.stderr.write(self.style.ERROR(f'  next: {e}'))
            try:
                events.extend(sofa.evenements_passes(tid, pages=opts['passes']))
            except sofa.SofaScoreErreur as e:
                self.stderr.write(self.style.ERROR(f'  last: {e}'))

            by_id: dict[int, dict] = {}
            for ev in events:
                eid = ev.get('id')
                if eid:
                    by_id[int(eid)] = ev
            events = list(by_id.values())
            self.stdout.write(f'  {len(events)} événements')
            self.stdout.flush()

            if dry:
                continue

            try:
                comp = self._competition(tid, meta)
            except Exception as e:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f'  competition: {e}'))
                continue

            for i, ev in enumerate(events, 1):
                close_old_connections()
                eid = ev.get('id')
                try:
                    # 1) Réseau hors transaction (ne doit jamais tenir un lock SQL).
                    remote = self._fetch_remote(ev, avec_contexte=avec_contexte)
                    # 2) Écriture courte.
                    with transaction.atomic():
                        created, updated, regle = self._persist_event(
                            comp, ev, remote,
                        )
                except Exception as e:  # noqa: BLE001
                    n_err += 1
                    self.stderr.write(f'  event {eid}: {e}')
                    continue

                if created:
                    n_new += 1
                elif updated:
                    n_upd += 1
                else:
                    n_skip += 1
                n_regles += regle
                ts = ev.get('startTimestamp')
                if ts:
                    jours.add(
                        sofa.ts_to_aware(ts).astimezone(
                            timezone.get_current_timezone()
                        ).date()
                    )
                if i % 10 == 0 or i == len(events):
                    self.stdout.write(f'  … {i}/{len(events)}')
                    self.stdout.flush()

        self.stdout.write(self.style.SUCCESS(
            f'Sync : {n_new} créés, {n_upd} mis à jour, {n_skip} inchangés, '
            f'{n_regles} options réglées'
            + (f', {n_err} erreurs' if n_err else '')
            + '.'
        ))

        if opts['calculer'] and not dry and jours:
            from django.core.management import call_command
            for jour in sorted(jours):
                close_old_connections()
                try:
                    call_command('calculer_analyses', journee=jour.isoformat())
                except Exception as e:  # noqa: BLE001
                    self.stderr.write(f'Calcul {jour} : {e}')

    def _fetch_remote(self, ev: dict, *, avec_contexte: bool) -> dict[str, Any]:
        """Appels SofaScore uniquement — zéro écriture DB."""
        eid = ev.get('id')
        out: dict[str, Any] = {
            'odds_1x2': None,
            'odds_ou25': None,
            'contexte': None,
        }
        if not eid:
            return out
        try:
            out['odds_1x2'] = sofa.cotes_1x2(int(eid))
        except sofa.SofaScoreErreur as e:
            self.stderr.write(f'  cotes 1X2 {eid}: {e}')
        try:
            out['odds_ou25'] = sofa.cotes_ou25(int(eid))
        except sofa.SofaScoreErreur as e:
            self.stderr.write(f'  cotes OU {eid}: {e}')

        if avec_contexte:
            home = ev.get('homeTeam') or {}
            away = ev.get('awayTeam') or {}
            try:
                out['contexte'] = sofa.collecter_contexte_match(
                    int(eid),
                    home_team_id=home.get('id'),
                    away_team_id=away.get('id'),
                    nom_dom=home.get('shortName') or home.get('name') or 'Dom',
                    nom_ext=away.get('shortName') or away.get('name') or 'Ext',
                    event=ev,
                    tournament_id=(ev.get('tournament') or {}).get('uniqueId')
                    or (ev.get('uniqueTournament') or {}).get('id'),
                )
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f'  contexte {eid}: {e}')
        return out

    def _competition(self, tid: int, meta: dict) -> Competition:
        with transaction.atomic():
            comp, _ = Competition.objects.update_or_create(
                code=meta['code'],
                defaults={
                    'nom': meta['nom'],
                    'pays': meta['pays'],
                    'ordre': meta['ordre'],
                    'actif': True,
                    'sofascore_id': tid,
                },
            )
        return comp

    def _equipe(self, team: dict) -> Equipe:
        sid = team.get('id')
        nom = (team.get('name') or 'Équipe')[:80]
        court = (team.get('shortName') or sofa.nom_court(nom))[:24]
        if sid:
            eq = Equipe.objects.filter(sofascore_id=sid).first()
            if eq:
                changed = False
                if eq.nom != nom:
                    eq.nom = nom
                    changed = True
                if eq.nom_court != court:
                    eq.nom_court = court
                    changed = True
                if changed:
                    eq.save()
                return eq
        eq = Equipe.objects.filter(nom=nom).first()
        if eq:
            if sid and not eq.sofascore_id:
                if not Equipe.objects.filter(sofascore_id=sid).exclude(pk=eq.pk).exists():
                    eq.sofascore_id = sid
                    eq.save(update_fields=['sofascore_id'])
            return eq
        base = sofa.slugify_nom(team.get('slug') or nom)
        slug = base
        i = 2
        while Equipe.objects.filter(slug=slug).exists():
            slug = f'{base}-{i}'
            i += 1
        return Equipe.objects.create(
            nom=nom, nom_court=court, slug=slug, sofascore_id=sid,
        )

    def _persist_event(
        self,
        comp: Competition,
        ev: dict,
        remote: dict[str, Any],
    ) -> tuple[bool, bool, int]:
        """Écriture DB pure — à appeler sous transaction.atomic()."""
        eid = ev.get('id')
        ts = ev.get('startTimestamp')
        if not eid or not ts:
            return False, False, 0
        coup = sofa.ts_to_aware(ts)
        if timezone.is_naive(coup):
            coup = timezone.make_aware(coup, dt_tz.utc)

        dom = self._equipe(ev['homeTeam'])
        ext = self._equipe(ev['awayTeam'])
        status_code = (ev.get('status') or {}).get('code')
        statut = sofa.statut_depuis_code(status_code)

        match = Match.objects.filter(sofascore_id=eid).first()
        created = False
        if match is None:
            match, created = Match.objects.update_or_create(
                domicile=dom,
                exterieur=ext,
                coup_denvoi=coup,
                defaults={
                    'competition': comp,
                    'statut': statut,
                    'sofascore_id': eid,
                    'journee': str((ev.get('roundInfo') or {}).get('round') or ''),
                },
            )
        else:
            if match.statut == 'termine' and statut == 'a_venir':
                statut = 'termine'
            match.competition = comp
            match.domicile = dom
            match.exterieur = ext
            match.coup_denvoi = coup
            match.statut = statut
            match.journee = str((ev.get('roundInfo') or {}).get('round') or '')
            match.save()

        n_regle = 0
        if statut == 'termine':
            bd, be, bdm, bem = sofa.scores_depuis_event(ev)
            fields = []
            if bd is not None and be is not None:
                match.buts_dom = bd
                match.buts_ext = be
                fields.extend(['buts_dom', 'buts_ext'])
            if bdm is not None and bem is not None:
                match.buts_dom_mt = bdm
                match.buts_ext_mt = bem
                fields.extend(['buts_dom_mt', 'buts_ext_mt'])
            if fields:
                match.save(update_fields=fields)
                n_regle = regler_match(match)

        now = timezone.now()
        odds = remote.get('odds_1x2')
        if odds:
            for sel, val in zip(('1', 'N', '2'), odds):
                Cote.objects.update_or_create(
                    match=match,
                    bookmaker='sofascore',
                    marche='1X2',
                    selection=sel,
                    defaults={'valeur': round(val, 3), 'nb_sources': 1, 'releve_le': now},
                )
        ou = remote.get('odds_ou25')
        if ou:
            for sel, val in zip(('over', 'under'), ou):
                Cote.objects.update_or_create(
                    match=match,
                    bookmaker='sofascore',
                    marche='OU25',
                    selection=sel,
                    defaults={'valeur': round(val, 3), 'nb_sources': 1, 'releve_le': now},
                )

        ctx = remote.get('contexte') or {}
        if any(ctx.values()):
            Contexte.objects.update_or_create(
                match=match,
                defaults={
                    **{k: v for k, v in ctx.items() if v},
                    'source': '',
                    'fiabilite': 'bonne',
                },
            )

        return created, not created, n_regle
