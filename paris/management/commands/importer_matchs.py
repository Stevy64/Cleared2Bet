from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from paris.import_json import ImportInvalide, valider_payload
from paris.models import Competition, Contexte, Cote, Equipe, Match

try:
    import json
except ImportError:  # pragma: no cover
    json = None


class Command(BaseCommand):
    help = 'Importe des matchs depuis le JSON d’analyse. Idempotent.'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, help='Fichier JSON')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        chemin = Path(opts['source'])
        if not chemin.exists():
            raise CommandError(f'Fichier introuvable : {chemin}')
        try:
            data = json.loads(chemin.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'JSON illisible : {exc}') from exc
        try:
            matchs = valider_payload(data)
        except ImportInvalide as exc:
            raise CommandError(str(exc)) from exc

        if opts['dry_run']:
            self.stdout.write(f'Dry-run : {len(matchs)} matchs valides, aucune écriture.')
            return

        n_matchs = n_cotes = 0
        with transaction.atomic():
            for m in matchs:
                n_matchs += 1
                n_cotes += self._importer_un(m)
        self.stdout.write(self.style.SUCCESS(
            f'Import OK : {n_matchs} matchs, {n_cotes} cotes écrites.'
        ))

    def _importer_un(self, m):
        comp_data = m['competition']
        competition, _ = Competition.objects.update_or_create(
            code=comp_data['code'],
            defaults={
                'nom': comp_data['nom'],
                'pays': comp_data.get('pays', ''),
                'ordre': comp_data.get('ordre', 100),
                'actif': comp_data.get('actif', True),
            },
        )
        domicile = self._equipe(m['domicile'])
        exterieur = self._equipe(m['exterieur'])
        coup = parse_datetime(m['coup_denvoi'])
        if coup is None:
            raise CommandError(f'coup_denvoi illisible : {m["coup_denvoi"]}')
        if timezone.is_naive(coup):
            coup = timezone.make_aware(coup, timezone.get_current_timezone())

        match, _ = Match.objects.update_or_create(
            domicile=domicile,
            exterieur=exterieur,
            coup_denvoi=coup,
            defaults={
                'competition': competition,
                'journee': m.get('journee', ''),
                'statut': m.get('statut', 'a_venir'),
            },
        )
        ctx = m.get('contexte') or {}
        Contexte.objects.update_or_create(
            match=match,
            defaults={
                'forme_dom': ctx.get('forme_dom', ''),
                'forme_ext': ctx.get('forme_ext', ''),
                'absents_dom': ctx.get('absents_dom', ''),
                'absents_ext': ctx.get('absents_ext', ''),
                'tendance_buts': ctx.get('tendance_buts', ''),
                'a_savoir': ctx.get('a_savoir', ''),
                'confrontations': ctx.get('confrontations', ''),
                'fiabilite': ctx.get('fiabilite', 'moyenne')[:8],
                'source': ctx.get('source', ''),
            },
        )
        releve = parse_datetime(m.get('releve_le') or '') or timezone.now()
        if timezone.is_naive(releve):
            releve = timezone.make_aware(releve, timezone.get_current_timezone())
        bookmaker = (m.get('cotes') or {}).get('bookmaker', 'consensus')
        n = 0
        unx2 = m['cotes']['1X2']
        for sel, val in (('1' , unx2['1']), ('N', unx2['N']), ('2', unx2['2'])):
            n += self._cote(match, bookmaker, '1X2', sel, val, releve)
        ou25 = m['cotes'].get('OU25')
        if ou25:
            n += self._cote(match, bookmaker, 'OU25', 'over', ou25['over'], releve)
            n += self._cote(match, bookmaker, 'OU25', 'under', ou25['under'], releve)
        return n

    def _equipe(self, data):
        equipe, _ = Equipe.objects.update_or_create(
            slug=data['slug'],
            defaults={'nom': data['nom'], 'nom_court': data['nom_court']},
        )
        return equipe

    def _cote(self, match, bookmaker, marche, selection, valeur, releve):
        Cote.objects.update_or_create(
            match=match,
            bookmaker=bookmaker,
            marche=marche,
            selection=selection,
            defaults={
                'valeur': Decimal(str(valeur)),
                'nb_sources': 1,
                'releve_le': releve,
            },
        )
        return 1
