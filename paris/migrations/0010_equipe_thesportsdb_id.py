from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paris', '0009_prop_unique_user_match'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipe',
            name='thesportsdb_id',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
    ]
