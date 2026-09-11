from django.db import migrations, models
import django.db.models.deletion


def premium_vers_vip(apps, schema_editor):
    Profil = apps.get_model('paris', 'Profil')
    Profil.objects.filter(categorie='premium').update(categorie='vip')


def vip_vers_premium(apps, schema_editor):
    Profil = apps.get_model('paris', 'Profil')
    Profil.objects.filter(categorie='vip').update(categorie='premium')


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('paris', '0004_profil'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profil',
            name='categorie',
            field=models.CharField(
                choices=[
                    ('membre', 'Membre'),
                    ('vip', 'VIP'),
                    ('premium', 'Premium'),
                ],
                db_index=True,
                default='membre',
                max_length=16,
            ),
        ),
        migrations.RunPython(premium_vers_vip, vip_vers_premium),
        migrations.CreateModel(
            name='MessageChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texte', models.CharField(max_length=400)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('auteur', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages_chat',
                    to='auth.user',
                )),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
