import datetime
from decimal import Decimal
from typing import Tuple, Union, TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

if TYPE_CHECKING:
    from datetime import date


class UserDataModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class CreditLine(UserDataModel):
    name = models.CharField("Name", max_length=255)
    holder = models.CharField("Holder", max_length=255)
    statement_date = models.PositiveSmallIntegerField(
        "Statement Date",
        default=1,
        help_text="The numbered day of each month that your statement posts.",
    )
    date_opened = models.DateField("Date Opened", default=timezone.now)
    annual_fee = models.DecimalField(
        "Annual Fee ($)", decimal_places=2, max_digits=9, default=0.0
    )
    interest_rate = models.DecimalField(
        "Interest Rate (%)", decimal_places=4, max_digits=9, default=0.0
    )
    credit_line = models.DecimalField(
        "Credit Line", decimal_places=2, max_digits=9, default=0.0
    )
    min_pay_pct = models.DecimalField(
        "Minimum Payment (%)", decimal_places=4, max_digits=9, default=0.0
    )
    min_pay_dlr = models.DecimalField(
        "Minimum Payment ($)", decimal_places=2, max_digits=9, default=0.0
    )
    priority = models.PositiveSmallIntegerField("Priority", default=0)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return self.name

    @property
    def balance(self) -> "Decimal":
        if self.statement_set.exists():
            return self.statement_set.order_by("year", "month").last().balance
        else:
            return self.credit_line

    @property
    def available_credit(self) -> "Decimal":
        return self.credit_line - self.balance

    @property
    def earliest_statement_date(self) -> Union["date", None]:
        if self.statement_set.exists():
            return self.statement_set.order_by("year", "month").first().date
        else:
            return None

    @property
    def latest_statement_date(self) -> Union["date", None]:
        if self.statement_set.exists():
            return self.statement_set.order_by("year", "month").last().date
        else:
            return None

    def get_absolute_url(self) -> str:
        return reverse("debt:account-detail", kwargs={"pk": self.pk})

    def min_pay(self, bal: Union["Decimal", None] = None) -> "Decimal":
        if bal is None:
            bal = self.balance
        return min(max(self.min_pay_dlr, self.min_pay_pct / 100 * bal), bal)

    def forecast_next(self, bal: Union["Decimal", None] = None) -> "Decimal":
        if bal is None:
            bal = self.balance
        return max(
            bal * (1 + self.interest_rate / 100 / 12) - self.min_pay(bal=bal),
            Decimal(0),
        )

    def calc_balance(
        self,
        month: int,
        year: int,
        prev_mo_bal: "Decimal",
        latest_stmnt_date: "date" = None,
        latest_bal: "Decimal" = None,
    ) -> Tuple["Decimal", Union["Decimal", None]]:
        """Calculates balance for an arbitrary month.

        Returns a tuple of balance, and minimum pay amount. There are
        three possibilities:

         1. There is a statement for the given month. In this case, that
            balance is returned and min pay is None.
         2. There is not a statement for the given month, but there are
            more recent statements. This means that the statement is
            simply missing. In this case, just assign the most recent
            balance. It will look a bit odd, but less odd than just
            making it 0, and it won't affect any of the forecasting. Min
            pay is also None in this case.
         3. The month/year comes after the most recent statement. It
            might be in the past or future, but in either case, we'll
            forecast the value assuming we're paying the minimum amount,
            and then take interest into account.

        Latest statement date is included as an optional keyword
        argument because you may want to call this function multiple
        times, so it essentially allows you to cache the property
        :func:`latest_statement_date`.

        Latest balance is for caching :func:`balance` in the same way.
        """
        latest_stmnt_date = latest_stmnt_date or self.latest_statement_date
        latest_bal = latest_bal or self.balance
        before_or_on_latest_statement = year < latest_stmnt_date.year or (
            month <= latest_stmnt_date.month and year == latest_stmnt_date.year
        )
        if before_or_on_latest_statement:
            try:
                # Hit the database to see if we have the actual value
                bal = self.statement_set.get(year=year, month=month).balance
                return bal, None
            except Statement.DoesNotExist:
                # If it's before this month and there's a more recent
                # statement, use the most recent statement value
                return latest_bal, None

        # Forecast the value instead
        bal = self.forecast_next(bal=prev_mo_bal)
        min_pay = self.min_pay(bal=prev_mo_bal)

        return bal, min_pay


class Statement(UserDataModel):
    account = models.ForeignKey(CreditLine, on_delete=models.CASCADE, null=True)
    year = models.PositiveSmallIntegerField("Year", default=0)
    month = models.PositiveSmallIntegerField("Month", default=0)
    balance = models.DecimalField("Balance", decimal_places=2, max_digits=9)

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = ("user", "account", "year", "month")

    def __str__(self):
        return f"{self.date.strftime('%b %Y')}: {self.balance}"

    def get_absolute_url(self) -> str:
        return reverse("debt:statement-update", kwargs={"pk": self.pk})

    @property
    def date(self) -> "date":
        return datetime.date(
            year=self.year, month=self.month, day=self.account.statement_date
        )
