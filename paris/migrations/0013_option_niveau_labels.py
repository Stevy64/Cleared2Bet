from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paris', '0012_option_niveau_recommandee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='option',
            name='niveau',
            field=models.CharField(
                choices=[
                    ('prudente', 'Prudent'),
                    ('recommandee', 'Recommandé'),
                    ('equilibree', 'Équilibrée'),
                    ('audacieuse', 'Audacieuse'),
                    ('filet', 'Sécurité'),
                    ('detail', 'Détail'),
                ],
                default='detail',
                max_length=12,
            ),
        ),
    ]
