"""Synchronise matchs, cotes 1X2/OU2.5, scores et H2H depuis SofaScore."""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timezone as dt_tz

from paris.models import Competition, Contexte, Cote, Equipe, Match
from paris.reglement import regler_match
from paris import sofascore as sofa


class Command(BaseCommand):
    help = (
        'Synchronise les matchs à venir / récents (cotes, scores, H2H) depuis '
        'SofaScore pour PL, LIGA, L1, SA, UCL.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--pages', type=int, default=2, help='Pages next/last')
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
            '--sans-contexte',
            action='store_true',
            help='Skip H2H/forme/météo (beaucoup plus rapide)',
        )

    def handle(self, *args, **opts):
        pages = opts['pages']
        dry = opts['dry_run']
        sans_contexte = opts['sans_contexte']
        n_new = n_upd = n_skip = n_regles = 0
        jours = set()

        for tid, meta in sofa.TOURNOIS.items():
            self.stdout.write(f'- {meta["code"]}...')
            self.stdout.flush()
            events: list[dict] = []
            try:
                events.extend(sofa.evenements_suivants(tid, pages=pages))
            except sofa.SofaScoreErreur as e:
                self.stderr.write(self.style.ERROR(f'  next: {e}'))
            try:
                events.extend(sofa.evenements_passes(tid, pages=opts['passes']))
            except sofa.SofaScoreErreur as e:
                self.stderr.write(self.style.ERROR(f'  last: {e}'))

            # Déduplique par id event (next + last peuvent se chevaucher).
            by_id: dict[int, dict] = {}
            for ev in events:
                eid = ev.get('id')
                if eid:
                    by_id[int(eid)] = ev
            events = list(by_id.values())
            self.stdout.write(f'  {len(events)} événements')
            self.stdout.flush()

            if dry:
                self.stdout.write(f'  dry-run : {len(events)} événements')
                continue

            # Un commit par match : une transaction géante bloquait tout
            # jusqu’à la fin d’un tournoi (plusieurs minutes sans match visible).
            comp = self._competition(tid, meta)
            for i, ev in enumerate(events, 1):
                try:
                    with transaction.atomic():
                        created, updated, regle = self._upsert_event(
                            comp, ev, avec_contexte=not sans_contexte,
                        )
                except Exception as e:  # noqa: BLE001
                    self.stderr.write(f'  event {ev.get("id")}: {e}')
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
            f'{n_regles} options réglées.'
        ))

        if opts['calculer'] and not dry and jours:
            from django.core.management import call_command
            for jour in sorted(jours):
                try:
                    call_command('calculer_analyses', journee=jour.isoformat())
                except Exception as e:  # noqa: BLE001 — commande métier
                    self.stderr.write(f'Calcul {jour} : {e}')

    def _competition(self, tid: int, meta: dict) -> Competition:
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
                # Ne pas écraser un id déjà pris par un doublon.
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

    def _upsert_event(
        self,
        comp: Competition,
        ev: dict,
        *,
        avec_contexte: bool = True,
    ) -> tuple[bool, bool, int]:
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
            # Ne pas rétrograder un match déjà réglé/terminé vers a_venir.
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

        # Cotes 1X2 + OU 2.5 (entrées du moteur).
        now = timezone.now()
        odds = sofa.cotes_1x2(eid)
        if odds:
            for sel, val in zip(('1', 'N', '2'), odds):
                Cote.objects.update_or_create(
                    match=match,
                    bookmaker='sofascore',
                    marche='1X2',
                    selection=sel,
                    defaults={'valeur': round(val, 3), 'nb_sources': 1, 'releve_le': now},
                )
        ou = sofa.cotes_ou25(eid)
        if ou:
            for sel, val in zip(('over', 'under'), ou):
                Cote.objects.update_or_create(
                    match=match,
                    bookmaker='sofascore',
                    marche='OU25',
                    selection=sel,
                    defaults={'valeur': round(val, 3), 'nb_sources': 1, 'releve_le': now},
                )

        # Contexte terrain (H2H, forme, absents, météo) — best-effort.
        if avec_contexte:
            try:
                ctx = sofa.collecter_contexte_match(
                    eid,
                    home_team_id=dom.sofascore_id,
                    away_team_id=ext.sofascore_id,
                    nom_dom=dom.nom_court,
                    nom_ext=ext.nom_court,
                    event=ev,
                    tournament_id=comp.sofascore_id,
                )
                if any(ctx.values()):
                    Contexte.objects.update_or_create(
                        match=match,
                        defaults={
                            **{k: v for k, v in ctx.items() if v},
                            'source': 'SofaScore',
                            'fiabilite': 'bonne',
                        },
                    )
            except Exception:  # noqa: BLE001 — ne jamais casser la sync
                pass

        return created, not created, n_regle
