# Generated manually for Profil

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('paris', '0003_voteoption'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categorie', models.CharField(
                    choices=[('membre', 'Membre'), ('premium', 'Premium')],
                    db_index=True,
                    default='membre',
                    max_length=16,
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profil',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
