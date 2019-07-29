# Generated by Django 2.1.7 on 2019-03-12 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0010_auto_20190311_1852'),
    ]

    operations = [
        migrations.AddField(
            model_name='statement',
            name='month',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Month'),
        ),
        migrations.AddField(
            model_name='statement',
            name='year',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Year'),
        ),
    ]