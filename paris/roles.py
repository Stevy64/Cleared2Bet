"""Rôles / catégories compte Cleared2Bet."""
from __future__ import annotations

CATEGORIES_VIP = frozenset({'vip', 'premium'})


def categorie_user(user) -> str:
    """visiteur | membre | vip (abonnement encore valide)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return 'visiteur'
    # Staff / superuser : VIP permanent (accès admin + app).
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return 'vip'
    from paris.models import Profil
    profil, _ = Profil.objects.get_or_create(user=user)
    if profil.abonnement_vip_actif:
        return 'vip'
    return 'membre'


def est_vip(user) -> bool:
    return categorie_user(user) == 'vip'


def payload_auth(user) -> dict:
    cat = categorie_user(user)
    vip_expire = None
    if user and getattr(user, 'is_authenticated', False):
        from paris.models import Profil
        profil = getattr(user, 'profil', None)
        if profil is None:
            profil, _ = Profil.objects.get_or_create(user=user)
        if cat == 'vip' and profil.vip_expire_le:
            vip_expire = profil.vip_expire_le.isoformat()
    return {
        'authentifie': bool(user and getattr(user, 'is_authenticated', False)),
        'username': user.username if user and getattr(user, 'is_authenticated', False) else None,
        'categorie': cat,
        'est_vip': cat == 'vip',
        'vip_expire_le': vip_expire,
    }
