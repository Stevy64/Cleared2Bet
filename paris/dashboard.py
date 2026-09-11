"""Stats activité plateforme pour le dashboard admin."""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from paris.chat import messages_actifs, seuil_expiration
from paris.models import Match, MessageChat, Option, Profil
from paris.roles import CATEGORIES_VIP


def _vip_actifs_qs():
    now = timezone.now()
    return Profil.objects.filter(categorie__in=CATEGORIES_VIP).filter(
        Q(vip_expire_le__isnull=True) | Q(vip_expire_le__gt=now),
    )


def build_dashboard_stats() -> dict:
    User = get_user_model()
    now = timezone.now()
    depuis_24h = now - timedelta(hours=24)
    depuis_7j = now - timedelta(days=7)

    n_users = User.objects.filter(is_active=True).count()
    n_vip = _vip_actifs_qs().count()
    n_membres = Profil.objects.filter(categorie='membre').count()
    n_matchs = Match.objects.filter(sofascore_id__isnull=False).count()
    n_a_venir = Match.objects.filter(
        sofascore_id__isnull=False, statut__in=('a_venir', 'en_cours'),
    ).count()
    tips_regles = Option.objects.filter(
        resultat__in=('gagne', 'perdu'),
        niveau__in=('prudente', 'filet'),
    )
    n_tips = tips_regles.count()
    n_gagnes = tips_regles.filter(resultat='gagne').count()
    n_msg_actifs = messages_actifs().count()
    n_msg_24h = MessageChat.objects.filter(created_at__gte=depuis_24h).count()
    n_inscrits_7j = User.objects.filter(date_joined__gte=depuis_7j).count()

    derniers_vip = list(
        _vip_actifs_qs()
        .select_related('user')
        .order_by('-vip_depuis', '-id')[:8]
    )
    derniers_msg = list(
        MessageChat.objects.filter(created_at__gte=seuil_expiration())
        .select_related('auteur')
        .order_by('-created_at')[:8]
    )

    return {
        'n_users': n_users,
        'n_vip': n_vip,
        'n_membres': n_membres,
        'n_matchs': n_matchs,
        'n_a_venir': n_a_venir,
        'n_tips': n_tips,
        'n_gagnes': n_gagnes,
        'taux_tips': round(100 * n_gagnes / n_tips) if n_tips else None,
        'n_msg_actifs': n_msg_actifs,
        'n_msg_24h': n_msg_24h,
        'n_inscrits_7j': n_inscrits_7j,
        'derniers_vip': derniers_vip,
        'derniers_msg': derniers_msg,
    }
