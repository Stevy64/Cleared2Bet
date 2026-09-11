"""Tests VIP + Salon VIP 24 h."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from paris.chat import messages_actifs, purger_messages_expires
from paris.models import MessageChat, Profil, ReglageSite
from paris.roles import categorie_user, est_vip, payload_auth
from paris.vip import ajouter_mois


class RolesVipTests(TestCase):
    def test_vip_et_premium_normalises(self):
        u = User.objects.create_user('vipuser', password='motdepasse123')
        profil, _ = Profil.objects.get_or_create(user=u)
        profil.activer_vip(mois=1)
        profil.save()
        self.assertEqual(categorie_user(u), 'vip')
        self.assertTrue(est_vip(u))

        profil.categorie = 'premium'
        profil.vip_expire_le = timezone.now() + timedelta(days=10)
        profil.save(update_fields=['categorie', 'vip_expire_le'])
        self.assertEqual(categorie_user(u), 'vip')
        self.assertTrue(est_vip(u))

        profil.categorie = 'membre'
        profil.save(update_fields=['categorie'])
        self.assertEqual(categorie_user(u), 'membre')
        self.assertFalse(est_vip(u))

    def test_vip_expire_apres_un_mois(self):
        u = User.objects.create_user('expire1', password='motdepasse123')
        profil, _ = Profil.objects.get_or_create(user=u)
        profil.activer_vip(mois=1)
        profil.save()
        self.assertTrue(est_vip(u))
        self.assertEqual(profil.vip_expire_le, ajouter_mois(profil.vip_depuis, 1))

        profil.vip_expire_le = timezone.now() - timedelta(seconds=1)
        profil.save(update_fields=['vip_expire_le'])
        self.assertFalse(est_vip(u))
        self.assertEqual(categorie_user(u), 'membre')
        payload = payload_auth(u)
        self.assertFalse(payload['est_vip'])

    def test_prolonger_ajoute_un_mois(self):
        u = User.objects.create_user('prolonge1', password='motdepasse123')
        profil, _ = Profil.objects.get_or_create(user=u)
        profil.activer_vip(mois=1)
        profil.save()
        fin1 = profil.vip_expire_le
        profil.prolonger_vip(mois=1)
        profil.save()
        self.assertEqual(profil.vip_expire_le, ajouter_mois(fin1, 1))
        self.assertTrue(est_vip(u))


class SalonVipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.membre = User.objects.create_user('membre1', password='motdepasse123')
        Profil.objects.get_or_create(user=self.membre, defaults={'categorie': 'membre'})
        self.vip = User.objects.create_user('vip1', password='motdepasse123')
        p, _ = Profil.objects.get_or_create(user=self.vip)
        p.activer_vip(mois=1)
        p.save()

    def test_salon_exige_auth(self):
        r = self.client.get('/api/v1/salon/')
        self.assertIn(r.status_code, (401, 403))

    def test_membre_refuse(self):
        self.client.force_authenticate(self.membre)
        r = self.client.get('/api/v1/salon/')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data.get('code'), 'vip_required')

    def test_vip_expire_refuse_salon(self):
        p = self.vip.profil
        p.vip_expire_le = timezone.now() - timedelta(hours=1)
        p.save(update_fields=['vip_expire_le'])
        self.client.force_authenticate(self.vip)
        r = self.client.get('/api/v1/salon/')
        self.assertEqual(r.status_code, 403)

    def test_vip_post_et_liste(self):
        self.client.force_authenticate(self.vip)
        r = self.client.post('/api/v1/salon/', {'texte': 'Salut les VIP'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['texte'], 'Salut les VIP')
        self.assertTrue(r.data['est_moi'])

        r2 = self.client.get('/api/v1/salon/')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.data['results']), 1)

    def test_purge_apres_24h(self):
        ancien = MessageChat.objects.create(auteur=self.vip, texte='vieux')
        MessageChat.objects.filter(pk=ancien.pk).update(
            created_at=timezone.now() - timedelta(hours=25),
        )
        MessageChat.objects.create(auteur=self.vip, texte='frais')
        n = purger_messages_expires()
        self.assertGreaterEqual(n, 1)
        self.assertEqual(messages_actifs().count(), 1)
        self.assertEqual(messages_actifs().first().texte, 'frais')


class InfoWhatsappTests(TestCase):
    def test_info_expose_lien_whatsapp(self):
        cfg = ReglageSite.get_solo()
        cfg.whatsapp_phone = '33612345678'
        cfg.whatsapp_message = 'Bonjour VIP'
        cfg.vip_tarif_libelle = 'VIP — test'
        cfg.save()
        client = APIClient()
        r = client.get('/api/v1/info/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('wa.me/33612345678', r.data.get('whatsapp_vip_url', ''))
        self.assertEqual(r.data.get('vip_tarif_libelle'), 'VIP — test')
