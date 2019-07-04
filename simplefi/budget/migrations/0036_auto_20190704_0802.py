# Generated by Django 2.2.3 on 2019-07-04 15:02

from django.db import migrations, models


def copy_fields_to_account(apps, schema_editor):
    Account = apps.get_model('budget.Account')
    db_alias = schema_editor.connection.alias

    # Copy fields over to each bank object
    for a in Account.objects.using(db_alias).all():
        a.date_col_name = a.bank.date_col_name
        a.amt_col_name = a.bank.amt_col_name
        a.desc_col_name = a.bank.desc_col_name
        a.save()


def copy_fields_to_bank(apps, schema_editor):
    Account = apps.get_model('budget.Account')
    db_alias = schema_editor.connection.alias

    # Copy fields over to each bank object
    for a in Account.objects.using(db_alias).all():
        a.bank.date_col_name = a.date_col_name
        a.bank.amt_col_name = a.amt_col_name
        a.bank.desc_col_name = a.desc_col_name
        a.bank.save()
        a.save()


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0035_auto_20190419_1954'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='amt_col_name',
            field=models.CharField(default='', max_length=255, verbose_name='Amount Header'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='date_col_name',
            field=models.CharField(default='', max_length=255, verbose_name='Date Header'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='desc_col_name',
            field=models.CharField(default='', max_length=255, verbose_name='Description Header'),
            preserve_default=False,
        ),
        migrations.RunPython(
            copy_fields_to_account,
            copy_fields_to_bank
        ),
    ]
