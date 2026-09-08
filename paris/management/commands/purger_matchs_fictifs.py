from django.core.management.base import BaseCommand
from django.db import transaction

from paris.models import Match


class Command(BaseCommand):
    help = (
        'Supprime les matchs sans sofascore_id (imports JSON de démo / fictifs). '
        'Les matchs synchronisés SofaScore sont conservés.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        qs = Match.objects.filter(sofascore_id__isnull=True)
        n = qs.count()
        if opts['dry_run']:
            self.stdout.write(f'Dry-run : {n} match(s) fictif(s) seraient supprimés.')
            for m in qs.select_related('domicile', 'exterieur', 'competition')[:50]:
                self.stdout.write(
                    f'  - {m.competition.code} {m.domicile.nom_court} – '
                    f'{m.exterieur.nom_court} ({m.coup_denvoi.isoformat()})'
                )
            return
        with transaction.atomic():
            deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Supprimé : {deleted} objet(s) liés aux matchs sans source externe '
            f'({n} matchs).'
        ))
