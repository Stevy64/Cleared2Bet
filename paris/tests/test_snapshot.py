"""Tests snapshot export / import."""

from django.test import TestCase
from django.utils import timezone

from paris.models import Analyse, Competition, Cote, Equipe, Match, Option
from paris.snapshot import exporter_snapshot, importer_snapshot


class SnapshotRoundtripTests(TestCase):
    def setUp(self):
        self.comp = Competition.objects.create(
            code='PL', nom='Premier League', ordre=20, sofascore_id=17,
        )
        self.dom = Equipe.objects.create(
            nom='Home FC', nom_court='Home', slug='home-fc', sofascore_id=1,
        )
        self.ext = Equipe.objects.create(
            nom='Away FC', nom_court='Away', slug='away-fc', sofascore_id=2,
        )
        self.match = Match.objects.create(
            competition=self.comp,
            domicile=self.dom,
            exterieur=self.ext,
            coup_denvoi=timezone.now(),
            statut='a_venir',
            sofascore_id=424242,
        )
        Cote.objects.create(
            match=self.match, bookmaker='snapshot', marche='1X2',
            selection='1', valeur='1.90', releve_le=timezone.now(),
        )
        Cote.objects.create(
            match=self.match, bookmaker='snapshot', marche='1X2',
            selection='N', valeur='3.40', releve_le=timezone.now(),
        )
        Cote.objects.create(
            match=self.match, bookmaker='snapshot', marche='1X2',
            selection='2', valeur='4.00', releve_le=timezone.now(),
        )
        ana = Analyse.objects.create(
            match=self.match,
            buts_dom_attendus=1.5, buts_ext_attendus=1.1,
            p1=0.45, pn=0.28, p2=0.27,
            score_probable='1-1', profil='moyen',
            marge_marche=0.05, residu=0.01, version_moteur='3.1.0',
        )
        Option.objects.create(
            analyse=ana, famille='Total buts', code='UN_2.5',
            libelle='Moins de 2,5 buts', probabilite=0.55,
            cote_juste=1.82, niveau='equilibree', origine='calcul',
        )

    def test_roundtrip(self):
        data = exporter_snapshot()
        self.assertEqual(len(data['matchs']), 1)
        self.assertEqual(data['matchs'][0]['sofascore_id'], 424242)
        self.assertIsNotNone(data['matchs'][0]['analyse'])

        Match.objects.all().delete()
        Equipe.objects.all().delete()
        Competition.objects.all().delete()

        stats = importer_snapshot(data)
        self.assertEqual(stats['matchs'], 1)
        self.assertEqual(stats['analyses'], 1)
        self.assertGreaterEqual(stats['options'], 1)
        m = Match.objects.get(sofascore_id=424242)
        self.assertEqual(m.domicile.slug, 'home-fc')
        self.assertTrue(hasattr(m, 'analyse'))
        self.assertEqual(m.analyse.options.count(), 1)
        # Logos navigateur : URL CDN dérivée de sofascore_id
        from paris.clubs import logo_url_pour
        self.assertIn('sofascore.com', logo_url_pour(m.domicile))
