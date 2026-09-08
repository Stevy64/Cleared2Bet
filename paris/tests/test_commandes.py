import json
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from paris.import_json import ImportInvalide, valider_payload
from paris.models import Match, Option
from paris.sofascore import formater_h2h, statut_depuis_code


EXEMPLE = Path(__file__).resolve().parents[2] / 'exemples' / 'journee-2026-09-08.json'


class ValidationImportTests(TestCase):
    def test_racine_invalide(self):
        with self.assertRaises(ImportInvalide):
            valider_payload([])

    def test_cote_invalide(self):
        data = json.loads(EXEMPLE.read_text(encoding='utf-8'))
        data['matchs'][0]['cotes']['1X2']['1'] = 0.9
        with self.assertRaises(ImportInvalide):
            valider_payload(data)

    def test_exemple_valide(self):
        data = json.loads(EXEMPLE.read_text(encoding='utf-8'))
        self.assertEqual(len(valider_payload(data)), 9)


class CommandesTests(TestCase):
    def test_import_dry_run_n_ecrit_pas(self):
        out = StringIO()
        call_command('importer_matchs', source=str(EXEMPLE), dry_run=True, stdout=out)
        self.assertEqual(Match.objects.count(), 0)
        self.assertIn('Dry-run', out.getvalue())

    def test_import_puis_calcul_idempotent(self):
        call_command('importer_matchs', source=str(EXEMPLE), stdout=StringIO())
        n = Match.objects.count()
        self.assertEqual(n, 9)
        call_command('importer_matchs', source=str(EXEMPLE), stdout=StringIO())
        self.assertEqual(Match.objects.count(), n)
        call_command('calculer_analyses', journee='2026-09-08', stdout=StringIO())
        m = Match.objects.select_related('analyse').first()
        self.assertTrue(hasattr(m, 'analyse'))
        n_opt = Option.objects.count()
        call_command('calculer_analyses', journee='2026-09-08', stdout=StringIO())
        self.assertEqual(Option.objects.count(), n_opt)

    def test_regler_apres_score(self):
        call_command('importer_matchs', source=str(EXEMPLE), stdout=StringIO())
        call_command('calculer_analyses', journee='2026-09-08', stdout=StringIO())
        m = Match.objects.first()
        m.buts_dom, m.buts_ext, m.statut = 2, 1, 'termine'
        m.save()
        out = StringIO()
        call_command('regler_options', stdout=out)
        self.assertIn('options réglées', out.getvalue())
        self.assertTrue(m.analyse.options.exclude(resultat='attente').exists())

    def test_import_fichier_invalide_echoue(self):
        with self.assertRaises(CommandError):
            call_command('importer_matchs', source='nexistepas.json')

    def test_recalcul_preserve_options_reglees(self):
        call_command('importer_matchs', source=str(EXEMPLE), stdout=StringIO())
        call_command('calculer_analyses', journee='2026-09-08', stdout=StringIO())
        m = Match.objects.filter(statut='a_venir').first()
        # Simule un match encore à venir dont une option a déjà été réglée (edge).
        opt = m.analyse.options.filter(niveau='prudente').first()
        opt.resultat = 'gagne'
        opt.save(update_fields=['resultat'])
        call_command('calculer_analyses', journee='2026-09-08', stdout=StringIO())
        opt.refresh_from_db()
        self.assertEqual(opt.resultat, 'gagne')


class SofaScoreHelpersTests(TestCase):
    def test_formater_h2h(self):
        texte = formater_h2h(
            {'teamDuel': {'homeWins': 3, 'awayWins': 1, 'draws': 2}},
            'PSG', 'OM',
        )
        self.assertIn('PSG 3', texte)
        self.assertIn('OM 1', texte)
        self.assertEqual(formater_h2h({}, 'A', 'B'), '')

    def test_statut_report(self):
        self.assertEqual(statut_depuis_code(60), 'reporte')
        self.assertEqual(statut_depuis_code(100), 'termine')
        self.assertEqual(statut_depuis_code(6), 'en_cours')
