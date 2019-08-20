import calendar
from decimal import Decimal
from typing import Any, Dict, List, Union, TYPE_CHECKING

from django.http import HttpRequest
from django.utils import timezone

from budget.models import Budget
from debt.models import CreditLine

if TYPE_CHECKING:
    from datetime import date, datetime

    from django.contrib.auth.models import User
    from django.db.models import QuerySet


def get_debt_budget(user: "User") -> Union["Budget", None]:
    """Gets the specified budget for debt, or None if not specified."""
    try:
        return Budget.objects.get(user=user, class_field__name="debt")
    except Budget.DoesNotExist:
        return None


class DebtSummaryTable:
    MAX_ROWS = 120

    def __init__(self, request: "HttpRequest", do_forecasting: bool = False):
        qs = CreditLine.objects.filter(
            user=request.user, credit_line__gt=0
        ).order_by("priority")
        self.accs = [cl for cl in qs if cl.statement_set.exists()]  # type: List[CreditLine]

        # Keep track of any warnings raised
        self.warnings = []  # type: List[str]

        # Cache latest statement dates, current balances and order
        self.latest_stmnts = {}  # type: Dict[str, date]
        self.balances = {}  # type: Dict[str, Decimal]
        self.names = []  # type: List[str]
        for a in self.accs:
            self.latest_stmnts[a.name] = a.latest_statement_date
            self.balances[a.name] = a.balance
            self.names.append(a.name)

        # Cache debt budget
        budget_obj = get_debt_budget(request.user)
        if budget_obj:
            self.debt_budget = abs(budget_obj.value)  # type: Decimal
        else:
            self.warnings.append("No debt budget specified")
            self.debt_budget = Decimal(0)  # type: Decimal

        # Get today
        self.now = timezone.now()  # type: datetime
        self.month = self.now.month  # type: int
        self.year = self.now.year  # type: int
        self.set_starting_month()

        # Start loop
        self.rows = []  # type: List[Dict[str, Any]]
        self.do_forecasting = do_forecasting
        self.calc_rows()

    def set_starting_month(self):
        earliest_dates = []
        for a in self.accs:
            d = a.earliest_statement_date
            if d is not None:
                earliest_dates.append(d)
        if not earliest_dates:
            self.warnings.append("No statement data for debt summary table")
            return
        earliest = min(earliest_dates)
        self.month = earliest.month
        self.year = earliest.year

    def formatted_rows(self) -> List[Dict[str, str]]:
        fmt_rows = []
        for row in self.rows:
            fmt_row = {}
            for k, v in row.items():
                try:
                    # Round float values
                    fmt_row[k] = format(v, ",.0f")
                except ValueError:
                    fmt_row[k] = v
            fmt_rows.append(fmt_row)
        return fmt_rows

    def increment(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1

    def break_loop(self) -> bool:
        if self.do_forecasting:
            if not self.rows:
                return False
            return self.rows[-1]["Total"] == 0 or len(self.rows) >= self.MAX_ROWS
        return self.after_this_month()

    def after_this_month(self) -> bool:
        return self.year > self.now.year or (
            self.month > self.now.month and self.year == self.now.year
        )

    def calc_rows(self):
        while not self.break_loop():
            self.calc_next_row()
            self.increment()

    def calc_next_row(self):
        row = {}  # Create the row
        min_pay = {}  # Keep track of minimum payments
        for a in self.accs:  # type: CreditLine
            prev_bal = self.rows[-1][a.name] if self.rows else self.balances[a.name]
            bal, min_pay_amt = a.calc_balance(
                self.month,
                self.year,
                prev_bal,
                latest_stmnt_date=self.latest_stmnts[a.name],
                latest_bal=self.balances[a.name],
            )
            row[a.name] = bal
            if min_pay_amt is not None:
                min_pay[a.name] = min_pay_amt

        # Spend the debt budget
        if self.after_this_month() and len(min_pay) == len(self.names):
            budget = self.debt_budget
            budget -= sum(min_pay.values())
            if budget > 0:
                for name in self.names:
                    if row[name] >= budget:
                        row[name] -= budget
                        break
                    else:
                        budget -= row[name]
                        row[name] = 0

        # Add total column
        row.update(Total=sum(row.values()))

        # Add month columns, then append to the table
        row.update(month=str(calendar.month_abbr[self.month]) + " " + str(self.year))
        self.rows.append(row)
