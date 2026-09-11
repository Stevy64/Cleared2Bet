"""Exporte matchs + analyses vers un JSON (pour PythonAnywhere / git pull)."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from paris.snapshot import exporter_snapshot

try:
    import json
except ImportError:  # pragma: no cover
    json = None


class Command(BaseCommand):
    help = (
        'Exporte les matchs réels (cotes, contexte, analyses) en JSON. '
        'À lancer en local après sync + calculer_analyses, puis commit/push '
        'pour importer sur PythonAnywhere.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--out',
            default='exports/matchs.json',
            help='Chemin du fichier JSON (défaut: exports/matchs.json)',
        )
        parser.add_argument(
            '--jours',
            type=int,
            default=None,
            help='Ne garder que les matchs dans ±N jours autour de maintenant.',
        )
        parser.add_argument(
            '--enrichir-clubs',
            action='store_true',
            help='Résout logos/fiches via API secours (plus lent, utile avant push PA).',
        )

    def handle(self, *args, **opts):
        chemin = Path(opts['out'])
        if not chemin.is_absolute():
            chemin = Path(settings.BASE_DIR) / chemin
        chemin.parent.mkdir(parents=True, exist_ok=True)

        data = exporter_snapshot(
            jours=opts.get('jours'),
            enrichir_clubs=bool(opts.get('enrichir_clubs')),
        )
        n = len(data.get('matchs') or [])
        if n == 0:
            raise CommandError(
                'Aucun match à exporter (base vide ou sans sofascore_id). '
                'Lance d’abord synchroniser_sofascore puis calculer_analyses.'
            )
        chemin.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        self.stdout.write(self.style.SUCCESS(
            f'Snapshot OK : {n} matchs → {chemin}'
        ))
