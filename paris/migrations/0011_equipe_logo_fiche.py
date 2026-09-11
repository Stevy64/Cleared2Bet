from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paris', '0010_equipe_thesportsdb_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipe',
            name='logo_externe',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='equipe',
            name='fiche_club',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
