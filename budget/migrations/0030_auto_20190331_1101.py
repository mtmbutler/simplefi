# Generated by Django 2.1.7 on 2019-03-31 18:01

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budget', '0029_auto_20190331_0848'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Subcategory',
            new_name='Category',
        ),
    ]
