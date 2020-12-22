import datetime

import django_tables2 as tables
from django.apps import apps

from debt import models


# -- ACCOUNTS --
class CreditLineTable(tables.Table):
    name = tables.Column(
        accessor="name", linkify=("debt:account-detail", {"pk": tables.A("pk")})
    )
    holder = tables.Column(accessor="holder")
    statement_date = tables.Column(accessor="statement_date")
    date_opened = tables.Column(accessor="date_opened")
    annual_fee = tables.Column(accessor="annual_fee")
    interest_rate = tables.Column(accessor="interest_rate")
    credit_line = tables.Column(accessor="credit_line")
    min_pay_pct = tables.Column(accessor="min_pay_pct")
    min_pay_dlr = tables.Column(accessor="min_pay_dlr")
    priority = tables.Column(accessor="priority")

    class Meta:
        model = models.CreditLine
        exclude = ("user", "id")
        fields = [
            "name",
            "holder",
            "statement_date",
            "date_opened",
            "annual_fee",
            "interest_rate",
            "credit_line",
            "min_pay_pct",
            "min_pay_dlr",
            "priority",
        ]


def linkify_statement(acc_name: str, mo_yr: str) -> str:
    url = None
    model = apps.get_model("debt.Statement")
    dt = datetime.datetime.strptime(mo_yr, "%b %Y")

    statement = model.objects.filter(
        account__name=acc_name, month=dt.month, year=dt.year
    ).first()
    if statement:
        url = statement.get_absolute_url()
    return url


class SummaryTable(tables.Table):
    month = tables.Column(accessor="month", orderable=False)
