# Generated by Django 2.1.7 on 2019-03-12 01:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0007_auto_20190311_0740'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='statement',
            options={'ordering': ['-date']},
        ),
        migrations.AlterField(
            model_name='account',
            name='annual_fee',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Annual Fee ($)'),
        ),
        migrations.AlterField(
            model_name='account',
            name='interest_rate',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Interest Rate (%)'),
        ),
        migrations.AlterField(
            model_name='account',
            name='statement_date',
            field=models.PositiveSmallIntegerField(default=1, help_text='The numbered day of each month that your statement posts.', verbose_name='Statement Date'),
        ),
        migrations.AlterUniqueTogether(
            name='statement',
            unique_together={('account', 'date')},
        ),
    ]