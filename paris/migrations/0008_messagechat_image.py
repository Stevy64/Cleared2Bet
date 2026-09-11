from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paris', '0007_vip_expire_le'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messagechat',
            name='texte',
            field=models.CharField(blank=True, default='', max_length=400),
        ),
        migrations.AddField(
            model_name='messagechat',
            name='image',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='salon/%Y/%m/%d/',
            ),
        ),
    ]
