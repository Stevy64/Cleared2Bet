"""Helpers salon de chat (rétention 24 h)."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from paris.models import MessageChat

RETENTION = timedelta(hours=24)


def seuil_expiration():
    return timezone.now() - RETENTION


def purger_messages_expires() -> int:
    anciens = list(
        MessageChat.objects.filter(created_at__lt=seuil_expiration()).only('id', 'image')
    )
    for msg in anciens:
        if msg.image:
            msg.image.delete(save=False)
    deleted, _ = MessageChat.objects.filter(
        pk__in=[m.pk for m in anciens],
    ).delete()
    return int(deleted)


def messages_actifs() -> QuerySet:
    return MessageChat.objects.filter(created_at__gte=seuil_expiration()).select_related('auteur')
