from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('paris', '0002_sofascore_propositions_votes'),
    ]

    operations = [
        migrations.CreateModel(
            name='VoteOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choix', models.CharField(choices=[('like', 'D’accord'), ('dislike', 'Pas d’accord')], max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('option', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='votes_consensus',
                    to='paris.option',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='votes_options',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name='voteoption',
            constraint=models.UniqueConstraint(fields=('option', 'user'), name='vote_unique_user_option'),
        ),
    ]
