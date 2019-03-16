# Generated by Django 2.1.7 on 2019-03-14 02:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0011_auto_20190312_0756'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='statement',
            options={'ordering': ['-year', '-month']},
        ),
        migrations.AlterUniqueTogether(
            name='statement',
            unique_together={('account', 'year', 'month')},
        ),
        migrations.RemoveField(
            model_name='statement',
            name='date',
        ),
    ]
