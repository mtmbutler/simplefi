import datetime

import pandas as pd
from django.apps import apps
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


MAX_ROWS = 120


def first_day_month_after(dt):
    if dt.month == 12:
        year = dt.year + 1
        month = 1
    else:
        year = dt.year
        month = dt.month + 1

    return datetime.date(year, month, 1)


def thirteen_months_ago():
    now = timezone.now()

    # Logic
    first_day_this_month = datetime.datetime(
        year=now.year, month=now.month, day=1, tzinfo=now.tzinfo
    )
    last_day_last_month = first_day_this_month - datetime.timedelta(days=1)
    first_day_last_month = datetime.datetime(
        year=last_day_last_month.year,
        month=last_day_last_month.month,
        day=1,
        tzinfo=now.tzinfo
    )
    return first_day_last_month - datetime.timedelta(days=365)


def oys_qs(user):
    Transaction = apps.get_model('budget.Transaction')
    base_qs = Transaction.objects.in_last_thirteen_months(user)

    # Group by
    grp_qs = (
        base_qs
            .annotate(month=TruncMonth('date'))
            .values('pattern__category__class_field__name', 'month')
            .annotate(s=Sum('amount'))
            # https://docs.djangoproject.com/en/dev/topics/db/aggregation/#interaction-with-default-ordering-or-order-by
            .order_by())

    # Pivot
    piv = pd.DataFrame(grp_qs).pivot(
        index='pattern__category__class_field__name',
        values='s', columns='month')
    piv = piv.fillna(0).astype(int)
    piv.loc['Total'] = piv.sum()  # Add total row

    # Rename and convert back to list of dicts
    piv.index.name = 'class_'
    piv.index = piv.index.str.title()
    piv.columns = [c.strftime('%b_%y') for c in piv.columns]
    new_qs = piv.reset_index().to_dict('records')

    return new_qs
