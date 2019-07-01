import datetime

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class UserDataModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    class Meta:
        abstract = True


class CreditLine(UserDataModel):
    name = models.CharField('Name', max_length=255)
    holder = models.CharField('Name', max_length=255)
    statement_date = models.PositiveSmallIntegerField(
        'Statement Date', default=1,
        help_text="The numbered day of each month that your statement posts."
    )
    date_opened = models.DateField('Date Opened', default=timezone.now)
    annual_fee = models.DecimalField('Annual Fee ($)', decimal_places=2,
                                     max_digits=9, default=0.)
    interest_rate = models.DecimalField('Interest Rate (%)', decimal_places=4,
                                        max_digits=9, default=0.)
    credit_line = models.DecimalField('Credit Line', decimal_places=2,
                                      max_digits=9, default=0.)
    min_pay_pct = models.DecimalField('Minimum Payment (%)', decimal_places=4,
                                      max_digits=9, default=0.)
    min_pay_dlr = models.DecimalField('Minimum Payment ($)', decimal_places=2,
                                      max_digits=9, default=0.)
    priority = models.PositiveSmallIntegerField('Priority', default=0)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    @property
    def balance(self):
        if self.statement_set.exists():
            return self.statement_set.order_by('year', 'month').last().balance
        else:
            return self.credit_line

    @property
    def available_credit(self):
        return self.credit_line - self.balance

    @property
    def earliest_statement_date(self):
        if self.statement_set.exists():
            return self.statement_set.order_by('year', 'month').first().date
        else:
            return None

    def get_absolute_url(self):
        return reverse('debt:account-detail', kwargs={'pk': self.pk})

    def min_pay(self, bal=None):
        if bal is None:
            bal = self.balance
        return max(self.min_pay_dlr, self.min_pay_pct / 100 * bal)

    def forecast_next(self, bal=None):
        if bal is None:
            bal = self.balance
        return max(bal * (1 + self.interest_rate / 100 / 12)
                   - self.min_pay(bal=bal), 0)


class Statement(UserDataModel):
    account = models.ForeignKey(CreditLine, on_delete=models.CASCADE, null=True)
    year = models.PositiveSmallIntegerField('Year', default=0)
    month = models.PositiveSmallIntegerField('Month', default=0)
    balance = models.DecimalField('Balance', decimal_places=2, max_digits=9)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('user', 'account', 'year', 'month')

    def __str__(self):
        return f"{self.date.strftime('%b %Y')}: {self.balance}"

    def get_absolute_url(self):
        return reverse('debt:statement-update', kwargs={'pk': self.pk})

    @property
    def date(self):
        return datetime.date(
            year=self.year, month=self.month, day=self.account.statement_date)
