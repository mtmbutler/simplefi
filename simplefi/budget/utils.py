import numpy as np
import pandas as pd
from django.utils import timezone

from .models import Account, Budget, Statement, Transaction


MAX_ROWS = 120


def one_year_summary(user, class_field=None):
    """Generates a DataFrame summarizing the last 13 months."""
    li = Transaction.objects.in_last_thirteen_months(user)
    if not li.exists():
        return pd.DataFrame()

    # Build DataFrame from query set
    if class_field is None:  # All
        df = pd.DataFrame([
            {'date': t.date,
             'amount': t.amount,
             'class_field': t.class_field.name}
            for t in li
        ])
    else:
        df = pd.DataFrame([
            {'date': t.date,
             'amount': t.amount,
             'subcategory': t.subcategory.name}
            for t in li.filter(pattern__subcategory__class_field=class_field)
        ])

    if df.empty:
        return df

    # Add datetime columns for grouping
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year

    # Pivot
    index = 'class_field' if class_field is None else 'subcategory'
    pivot = pd.pivot_table(df, values='amount', index=index,
                           columns=['year', 'month'], aggfunc=np.sum)
    pivot = pivot.fillna(0)

    # Add total row
    pivot.loc['Total', :] = pivot.sum()

    return pivot


def debt_summary(user):
    """Generates a DataFrame showing the path out of debt."""
    accs = Account.objects.filter(user=user, credit_line__gt=0)

    # Get starting point
    earliest_dates = []
    for a in accs:
        d = a.earliest_statement_date
        if d is not None:
            earliest_dates.append(d)
    if not earliest_dates:
        return pd.DataFrame()
    earliest = min(earliest_dates)
    month = earliest.month
    year = earliest.year

    # Get today
    now = timezone.now()

    # Start loop
    rows = []
    count = 0
    while True:
        # Create the row
        row = {}
        min_pay = {}  # Keep track of minimum payments
        for a in accs:
            try:  # See if we have the actual statement value
                row[a.name] = a.statement_set.get(
                    year=year, month=month).balance
            except Statement.DoesNotExist:
                # If it's before this month, set to balance
                if year < now.year or (month < now.month and year == now.year):
                    row[a.name] = a.statement_set.order_by('year', 'month').first().balance
                else:
                    # Forecast the value instead
                    prev_bal = rows[-1][a.name] if rows else a.balance
                    row[a.name] = a.forecast_next(bal=prev_bal)
                    min_pay[a.name] = a.min_pay(bal=prev_bal)

        # Spend the debt budget
        if len(min_pay) == accs.count():
            debt_budget = Budget.objects.get(
                user=user, class_field__name='debt')
            budget = abs(debt_budget.value)
            budget -= sum(min_pay.values())
            for a in accs.order_by('priority'):
                if row[a.name] >= budget:
                    row[a.name] -= budget
                    break
                else:
                    budget -= row[a.name]
                    row[a.name] = 0
        row.update(Total=sum(row.values()))
        row.update(year=year, month=month)
        rows.append(row)

        # Exit condition
        if row['Total'] == 0:
            break
        elif count >= MAX_ROWS:
            break

        # Increment
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        count += 1
    col_order = [a.name for a in accs.order_by('priority')] + ['Total']
    df = pd.DataFrame(
        rows).set_index(['year', 'month']).astype(int)
    df = df[col_order]

    return df
