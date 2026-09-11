"""Secours TheSportsDB + fiche club sans provenance exposée."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from paris.models import Competition, Equipe, Match
from paris import thesportsdb as tsdb


class TheSportsDbHelpersTests(TestCase):
    def test_aliases_psg(self):
        # Ne frappe pas le réseau si déjà mockable ; on teste juste la résolution d’alias.
        self.assertEqual(tsdb._ALIASES[tsdb._norm('PSG')], 'Paris Saint Germain')

    def test_saison_str_aout(self):
        from datetime import date
        self.assertEqual(tsdb.saison_str(date(2026, 9, 11)), '2026-2027')
        self.assertEqual(tsdb.saison_str(date(2026, 3, 1)), '2025-2026')


class EquipeInfosApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.comp = Competition.objects.create(code='PL', nom='Premier League', ordre=1)
        self.eq = Equipe.objects.create(
            nom='Liverpool FC', nom_court='Liverpool', slug='liverpool-fc', sofascore_id=44,
        )
        Match.objects.create(
            competition=self.comp,
            domicile=self.eq,
            exterieur=Equipe.objects.create(nom='Fulham FC', nom_court='Fulham', slug='fulham-fc'),
            coup_denvoi=timezone.now(),
            statut='termine',
            buts_dom=2,
            buts_ext=1,
            sofascore_id=999001,
        )

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    })
    def test_infos_ne_expose_pas_source(self):
        r = self.client.get(f'/api/v1/equipes/{self.eq.id}/infos/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('source', r.data)
        self.assertEqual(r.data.get('nom'), 'Liverpool FC')
        self.assertIn('forme', r.data)
        self.assertIn('recents', r.data)

    def test_contexte_api_sans_source(self):
        from paris.models import Contexte, Analyse
        from paris.serializers import ContexteSerializer
        m = Match.objects.first()
        Contexte.objects.create(match=m, forme_dom='test', source='ne-pas-exposer')
        data = ContexteSerializer(m.contexte).data
        self.assertNotIn('source', data)
