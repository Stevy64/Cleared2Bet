"""Calcule les analyses moteur pour une journée (date locale Europe/Paris)."""

from datetime import datetime, time as dt_time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from paris.models import Analyse, Match, Option
from paris.moteur import AnalyseInvalide, VERSION_MOTEUR, analyser, classer_journee, selections_niveaux, uniformite_excessive


# Ordre de préférence bookmaker quand plusieurs cotes existent pour le même marché.
_BOOK_PRIO = ('sofascore', 'consensus', 'PMUG')


class Command(BaseCommand):
    help = (
        'Calcule les analyses pour une journée (date ISO). '
        'Ignore les matchs terminés/reportés ; préserve les options déjà réglées.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--journee', required=True, help='Date AAAA-MM-JJ')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        jour = parse_date(opts['journee'])
        if jour is None:
            raise CommandError(f'Date invalide : {opts["journee"]}')
        tz = timezone.get_current_timezone()
        debut = timezone.make_aware(datetime.combine(jour, dt_time.min), tz)
        fin = timezone.make_aware(datetime.combine(jour, dt_time.max), tz)

        matchs = list(
            Match.objects.filter(
                coup_denvoi__gte=debut,
                coup_denvoi__lte=fin,
            )
            .exclude(statut__in=('termine', 'reporte'))
            .select_related('domicile', 'exterieur')
            .prefetch_related('cotes')
        )
        if not matchs:
            raise CommandError(
                f'Aucun match à analyser le {jour.isoformat()} '
                f'(hors terminés/reportés).'
            )

        analyses = []
        ignores = 0
        for match in matchs:
            cotes_1x2, cotes_ou = self._cotes(match)
            if cotes_1x2 is None:
                ignores += 1
                continue
            try:
                payload = analyser(
                    cotes_1x2,
                    cotes_ou,
                    match.domicile.nom_court,
                    match.exterieur.nom_court,
                )
            except AnalyseInvalide as e:
                self.stderr.write(f'  ignore {match}: {e}')
                ignores += 1
                continue
            analyses.append((match, payload))

        if not analyses:
            raise CommandError(
                f'Aucun match avec cotes 1X2 valides le {jour.isoformat()} '
                f'({ignores} ignorés).'
            )
        if ignores:
            self.stdout.write(f'{ignores} match(s) sans cotes 1X2 utilisables ignorés.')

        payloads = [a for _, a in analyses]
        classer_journee(payloads)
        sels = [selections_niveaux(p['options']) for p in payloads]
        if uniformite_excessive(sels):
            self.stdout.write(self.style.WARNING(
                'Uniformité élevée détectée sur la journée '
                '(correction douce appliquée si alternatives disponibles).'
            ))

        if opts['dry_run']:
            self.stdout.write(f'Dry-run : {len(analyses)} analyses, aucune écriture.')
            return

        n_opt = 0
        with transaction.atomic():
            for match, payload in analyses:
                n_opt += self._sauver(match, payload)
        self.stdout.write(self.style.SUCCESS(
            f'{len(analyses)} analyses, {n_opt} options (moteur {VERSION_MOTEUR}).'
        ))

    def _cotes(self, match):
        """Choisit les cotes les plus récentes, en privilégiant sofascore/consensus."""
        meilleurs = {}  # (marche, selection) -> (prio, releve_le, valeur)
        for c in match.cotes.all():
            key = (c.marche, c.selection)
            try:
                prio = _BOOK_PRIO.index(c.bookmaker)
            except ValueError:
                prio = len(_BOOK_PRIO)
            cand = (prio, c.releve_le, float(c.valeur))
            prev = meilleurs.get(key)
            if prev is None or cand[0] < prev[0] or (cand[0] == prev[0] and cand[1] > prev[1]):
                meilleurs[key] = cand

        by = {k: v[2] for k, v in meilleurs.items()}
        try:
            unx2 = (by[('1X2', '1')], by[('1X2', 'N')], by[('1X2', '2')])
        except KeyError:
            return None, None
        ou = None
        if ('OU25', 'over') in by and ('OU25', 'under') in by:
            ou = (by[('OU25', 'over')], by[('OU25', 'under')])
        return unx2, ou

    def _sauver(self, match, payload):
        """Met à jour l’analyse sans effacer les options déjà réglées ni leurs votes."""
        analyse, _ = Analyse.objects.update_or_create(
            match=match,
            defaults={
                'buts_dom_attendus': payload['buts_dom_attendus'],
                'buts_ext_attendus': payload['buts_ext_attendus'],
                'p1': payload['p1'],
                'pn': payload['pn'],
                'p2': payload['p2'],
                'score_probable': payload['score_probable'],
                'profil': payload['profil'],
                'marge_marche': payload['marge_marche'],
                'residu': payload['residu'],
                'version_moteur': payload['version_moteur'],
            },
        )
        existing = {o.code: o for o in analyse.options.all()}
        seen = set()
        n = 0
        for o in payload['options']:
            seen.add(o['code'])
            old = existing.get(o['code'])
            if old is None:
                Option.objects.create(
                    analyse=analyse,
                    famille=o['famille'],
                    code=o['code'],
                    libelle=o['libelle'],
                    probabilite=o['probabilite'],
                    cote_juste=o['cote_juste'],
                    niveau=o['niveau'],
                    origine=o['origine'],
                )
                n += 1
                continue
            # Ne jamais écraser un règlement (gagne/perdu/annule).
            old.famille = o['famille']
            old.libelle = o['libelle']
            old.probabilite = o['probabilite']
            old.cote_juste = o['cote_juste']
            old.origine = o['origine']
            if old.resultat == 'attente':
                old.niveau = o['niveau']
            old.save()
            n += 1

        # Supprime seulement les options encore en attente et absentes du nouveau run.
        for code, old in existing.items():
            if code not in seen and old.resultat == 'attente':
                old.delete()
        return n
