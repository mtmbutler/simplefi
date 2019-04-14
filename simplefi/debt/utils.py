import pandas as pd
from django.utils import timezone

from debt.models import CreditLine, Statement


MAX_ROWS = 120


def debt_summary(user):
    """Generates a DataFrame showing the path out of debt."""
    accs = CreditLine.objects.filter(user=user, credit_line__gt=0)

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
            budget = 1700  # Todo
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
