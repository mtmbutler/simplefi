# Generated by Django 2.1.7 on 2019-03-19 14:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budget', '0012_auto_20190313_1936'),
    ]

    operations = [
        migrations.AddField(
            model_name='bank',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='bank',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Name'),
        ),
        migrations.AlterUniqueTogether(
            name='bank',
            unique_together={('user', 'name')},
        ),
    ]
