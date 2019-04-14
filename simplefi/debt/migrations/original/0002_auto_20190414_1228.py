# Generated by Django 2.1.7 on 2019-04-14 19:28

from django.db import migrations


def copy_data_to_debt_app(apps, schema_editor):
    b_AccountHolder = apps.get_model('budget.AccountHolder')
    b_Account = apps.get_model('budget.Account')
    b_Statement = apps.get_model('budget.Statement')
    d_AccountHolder = apps.get_model('debt.AccountHolder')
    d_CreditLine = apps.get_model('debt.CreditLine')
    d_Statement = apps.get_model('debt.Statement')
    db_alias = schema_editor.connection.alias

    for b_ah in b_AccountHolder.objects.using(db_alias).all():
        d_AccountHolder.objects.using(db_alias).create(
            id=b_ah.id, user=b_ah.user, name=b_ah.name)

    for b_a in b_Account.objects.using(db_alias).all():
        d_CreditLine.objects.using(db_alias).create(
            id=b_a.id,
            user=b_a.user,
            name=b_a.name,
            holder_id=b_a.holder_id,
            statement_date=b_a.statement_date,
            date_opened=b_a.date_opened,
            annual_fee=b_a.annual_fee,
            interest_rate=b_a.interest_rate,
            credit_line=b_a.credit_line,
            min_pay_pct=b_a.min_pay_pct,
            min_pay_dlr=b_a.min_pay_dlr,
            priority=b_a.priority)

    for b_s in b_Statement.objects.using(db_alias).all():
        d_Statement.objects.using(db_alias).create(
            id=b_s.id,
            user=b_s.user,
            account_id=b_s.account_id,
            year=b_s.year,
            month=b_s.month,
            balance=b_s.balance)


class Migration(migrations.Migration):

    dependencies = [
        ('debt', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(copy_data_to_debt_app, migrations.RunPython.noop),
    ]