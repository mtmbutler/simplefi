import datetime

import django_tables2 as tables
from django.apps import apps


def linkify_statement(acc_name: str, mo_yr: str) -> str:
    model = apps.get_model('debt.Statement')
    dt = datetime.datetime.strptime(mo_yr, '%b %Y')

    statement = model.objects.filter(
        account__name=acc_name, month=dt.month, year=dt.year).first()
    if statement:
        return statement.get_absolute_url()


class SummaryTable(tables.Table):
    month = tables.Column(accessor='month', orderable=False)
