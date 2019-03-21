# Generated by Django 2.1.7 on 2019-03-21 02:45

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budget', '0021_auto_20190320_1942'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='accountholder',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='pattern',
            name='pattern',
            field=models.CharField(max_length=255, verbose_name='Match Pattern'),
        ),
        migrations.AlterField(
            model_name='subcategory',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Name'),
        ),
        migrations.AlterUniqueTogether(
            name='account',
            unique_together={('user', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='accountholder',
            unique_together={('user', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('user', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='pattern',
            unique_together={('user', 'pattern')},
        ),
        migrations.AlterUniqueTogether(
            name='statement',
            unique_together={('user', 'account', 'year', 'month')},
        ),
        migrations.AlterUniqueTogether(
            name='subcategory',
            unique_together={('user', 'category', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='transaction',
            unique_together={('user', 'account', 'date', 'amount', 'description')},
        ),
    ]
