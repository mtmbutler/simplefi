# Generated by Django 2.2.3 on 2019-07-04 15:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0036_auto_20190704_0802'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='bank',
        ),
    ]
