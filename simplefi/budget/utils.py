import datetime
from typing import Dict, List, Union, TYPE_CHECKING

import pandas as pd
from django.apps import apps
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

if TYPE_CHECKING:
    from datetime import date, datetime

    from django.contrib.auth.models import User

MAX_ROWS = 120


def first_day_month_after(dt: Union['datetime', 'date']) -> 'date':
    """The first day of the next month."""
    if dt.month == 12:  # December edge case
        return datetime.date(dt.year + 1, 1, 1)
    return datetime.date(dt.year, dt.month + 1, 1)


def thirteen_months_ago(dt: 'datetime' = None) -> 'datetime':
    """The first day of the previous month, last year.

    Example:
        If today is 15 Mar 2000, then this function will return
        1 Feb 1999.
    """
    dt = dt or timezone.now()

    # Logic
    first_day_this_month = datetime.datetime(
        year=dt.year, month=dt.month, day=1, tzinfo=dt.tzinfo)
    last_day_last_month = first_day_this_month - datetime.timedelta(days=1)
    first_day_last_month = datetime.datetime(
        year=last_day_last_month.year,
        month=last_day_last_month.month,
        day=1,
        tzinfo=dt.tzinfo)
    return first_day_last_month - datetime.timedelta(days=365)


def safe_strftime(dt: Union['datetime', str], fmt: str) -> str:
    if isinstance(dt, str):
        return dt
    return dt.strftime(fmt)


def oys_qs(
    user: 'User', class_id: int = None
) -> List[Dict[str, Union[str, int]]]:
    """The query set for a pivot table.

    The columns are always month/year combinations, i.e. Aug 2000,
    Sep 2000, etc.

    If class_id is none, the rows are all the classes. If defined, the
    rows are all the categories defined for the defined class.

    The values are the sum of all transactions for the given row/column.
    """
    Transaction = apps.get_model('budget.Transaction')
    Budget = apps.get_model('budget.Budget')

    if class_id is None:
        base_qs = Transaction.objects.in_last_thirteen_months(user)
        ix = 'pattern__category__class_field__name'
        piv_ix_name = 'class_'
    else:
        base_qs = Transaction.objects.in_last_thirteen_months(
            user,
            pattern__category__class_field_id=class_id)
        ix = 'pattern__category__name'
        piv_ix_name = 'category'

    # Group by
    grp_qs = (
        base_qs
        .annotate(month=TruncMonth('date'))
        .values(ix, 'month')
        .annotate(s=Sum('amount'))
        # https://docs.djangoproject.com/en/dev/topics/db/aggregation/#interaction-with-default-ordering-or-order-by
        .order_by())

    if not grp_qs:
        return grp_qs

    # Pivot
    piv = pd.DataFrame(grp_qs).pivot(
        index=ix,
        values='s', columns='month')

    # Add budget col and title-ify index if in class mode
    if class_id is None:
        piv['budget'] = [
            getattr(Budget.objects.get(class_field__name=c, user=user), 'value', 0)
            for c in piv.index]
        piv.index = piv.index.str.title()
    piv = piv.fillna(0).astype(int)
    piv.loc['Total'] = piv.sum()  # Add total row

    # Rename and convert back to list of dicts
    piv.index.name = piv_ix_name
    piv.columns = [safe_strftime(c, '%b_%y') for c in piv.columns]
    new_qs = piv.reset_index().to_dict('records')

    return new_qs
