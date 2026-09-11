"""Abonnement VIP — durée 1 mois, prolongation manuelle."""
from __future__ import annotations

import calendar
from datetime import datetime

from django.utils import timezone


def ajouter_mois(dt: datetime, mois: int = 1) -> datetime:
    """Ajoute N mois calendaires en conservant l’heure (jour borné au mois cible)."""
    if mois == 0:
        return dt
    y, m = dt.year, dt.month + mois
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    jour = min(dt.day, calendar.monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=jour)


def debut_abonnement(mois: int = 1) -> tuple[datetime, datetime]:
    """Retourne (début, expiration) pour un nouvel abonnement de N mois."""
    debut = timezone.now()
    return debut, ajouter_mois(debut, mois)


def nouvelle_expiration(expire_actuelle, mois: int = 1) -> datetime:
    """Prolonge à partir de max(maintenant, fin actuelle)."""
    maintenant = timezone.now()
    base = expire_actuelle if expire_actuelle and expire_actuelle > maintenant else maintenant
    return ajouter_mois(base, mois)
