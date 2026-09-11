from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('paris', '0008_messagechat_image'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='propositionparis',
            constraint=models.UniqueConstraint(
                fields=('match', 'auteur'),
                name='prop_unique_user_match',
            ),
        ),
    ]
