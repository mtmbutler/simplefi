# Generated by Django 2.1.7 on 2019-03-21 02:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0018_auto_20190320_1931'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pattern',
            name='subcategory',
        ),
        migrations.RemoveField(
            model_name='statement',
            name='account',
        ),
        migrations.RemoveField(
            model_name='subcategory',
            name='category',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='account',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='category',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='pattern',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='subcategory',
        ),
        migrations.RemoveField(
            model_name='upload',
            name='account',
        ),
    ]