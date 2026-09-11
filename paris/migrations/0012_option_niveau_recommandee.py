from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paris', '0011_equipe_logo_fiche'),
    ]

    operations = [
        migrations.AlterField(
            model_name='option',
            name='niveau',
            field=models.CharField(
                choices=[
                    ('prudente', 'Prudente'),
                    ('recommandee', 'Recommandée'),
                    ('equilibree', 'Équilibrée'),
                    ('audacieuse', 'Audacieuse'),
                    ('filet', 'Filet de sécurité'),
                    ('detail', 'Détail'),
                ],
                default='detail',
                max_length=12,
            ),
        ),
    ]
