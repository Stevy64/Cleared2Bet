from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paris', '0005_vip_messagechat'),
    ]

    operations = [
        migrations.AddField(
            model_name='profil',
            name='note_admin',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='profil',
            name='vip_depuis',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='ReglageSite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('whatsapp_phone', models.CharField(
                    blank=True, help_text='Numéro international sans + (ex. 33612345678).', max_length=32,
                )),
                ('whatsapp_message', models.CharField(
                    blank=True,
                    default='Bonjour, je souhaite devenir VIP sur Cleared2Bet.',
                    help_text='Message prérempli quand l’utilisateur ouvre WhatsApp.',
                    max_length=300,
                )),
                ('whatsapp_url', models.URLField(
                    blank=True, help_text='Lien WhatsApp complet (prioritaire si renseigné).',
                )),
                ('vip_tarif_libelle', models.CharField(
                    blank=True, default='VIP Cleared2Bet',
                    help_text='Court libellé affiché sur le CTA (ex. « VIP — 4,99 € / mois »).',
                    max_length=120,
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Réglages site',
                'verbose_name_plural': 'Réglages site',
            },
        ),
        migrations.AlterModelOptions(
            name='messagechat',
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Message Salon VIP',
                'verbose_name_plural': 'Messages Salon VIP',
            },
        ),
    ]
