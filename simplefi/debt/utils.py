import calendar
from typing import Dict, List, Union, TYPE_CHECKING

from django.contrib import messages
from django.http import HttpRequest
from django.utils import timezone

from budget.models import Budget
from debt.models import CreditLine, Statement

if TYPE_CHECKING:
    from django.contrib.auth.models import User


MAX_ROWS = 120


def get_debt_budget(user: 'User') -> Union['Budget', None]:
    """Gets the specified budget for debt, or None if not specified."""
    try:
        return Budget.objects.get(user=user, class_field__name='debt')
    except Budget.DoesNotExist:
        return None


def debt_summary(request: 'HttpRequest') -> List[Dict[str, str]]:
    """Generates a table showing the path out of debt."""
    accs = CreditLine.objects.filter(user=request.user, credit_line__gt=0)

    # Get starting point
    earliest_dates = []
    for a in accs:
        d = a.earliest_statement_date
        if d is not None:
            earliest_dates.append(d)
    if not earliest_dates:
        return []
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
                    row[a.name] = a.statement_set.order_by(
                        'year', 'month').first().balance
                else:
                    # Forecast the value instead
                    prev_bal = rows[-1][a.name] if rows else a.balance
                    row[a.name] = a.forecast_next(bal=prev_bal)
                    min_pay[a.name] = a.min_pay(bal=prev_bal)

        # Spend the debt budget
        budget_obj = get_debt_budget(request.user)
        if budget_obj is None:
            messages.warning(request, "No debt budget specified.")
        elif len(min_pay) == accs.count():
            budget = abs(budget_obj.value)
            budget -= sum(min_pay.values())
            if budget > 0:
                for a in accs.order_by('priority'):
                    if row[a.name] >= budget:
                        row[a.name] -= budget
                        break
                    else:
                        budget -= row[a.name]
                        row[a.name] = 0

        # Add total column
        row.update(Total=sum(row.values()))

        # Add month columns, then append to the table
        row.update(month=str(calendar.month_abbr[month]) + " " + str(year))
        rows.append(row)

        # Exit condition
        if row['Total'] == 0 or count >= MAX_ROWS:
            # Round float values
            for row in rows:
                for k, v in row.items():
                    try:
                        row[k] = format(v, ',.0f')
                    except ValueError:
                        pass
            break

        # Increment
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        count += 1

    return rows
