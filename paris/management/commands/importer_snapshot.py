"""Importe un snapshot JSON (matchs + analyses) généré en local."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from paris.snapshot import importer_snapshot

try:
    import json
except ImportError:  # pragma: no cover
    json = None


class Command(BaseCommand):
    help = (
        'Importe data/snapshots/matchs.json (ou --source). '
        'Usage typique sur PythonAnywhere après git pull.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            default='exports/matchs.json',
            help='Fichier JSON snapshot',
        )
        parser.add_argument(
            '--recalculer',
            action='store_true',
            help='Après import, relance calculer_analyses (moteur local).',
        )

    def handle(self, *args, **opts):
        chemin = Path(opts['source'])
        if not chemin.is_absolute():
            chemin = Path(settings.BASE_DIR) / chemin
        if not chemin.exists():
            raise CommandError(
                f'Fichier introuvable : {chemin}\n'
                'Sur ta machine locale : sync + exporter_snapshot, commit/push, '
                'puis git pull ici.'
            )
        try:
            data = json.loads(chemin.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'JSON illisible : {exc}') from exc

        stats = importer_snapshot(data)
        self.stdout.write(self.style.SUCCESS(
            'Import snapshot OK : '
            + ', '.join(f'{k}={v}' for k, v in stats.items())
        ))

        if opts['recalculer']:
            from django.core.management import call_command
            self.stdout.write('Recalcul des analyses (moteur local)…')
            call_command('calculer_analyses')
