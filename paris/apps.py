from django.apps import AppConfig


class ParisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'paris'
    verbose_name = 'Cleared2Bet'

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        from paris.models import Profil

        User = get_user_model()

        def assurer_profil(sender, instance, created, **kwargs):
            if created:
                Profil.objects.get_or_create(user=instance)

        post_save.connect(assurer_profil, sender=User, dispatch_uid='paris_profil_user')

