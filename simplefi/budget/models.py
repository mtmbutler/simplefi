import datetime

import pandas as pd
from django.db import models, IntegrityError
from django.urls import reverse
from django.utils import timezone


class TransactionManager(models.Manager):
    @staticmethod
    def in_last_thirteen_months():
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
        start_date = first_day_last_month - datetime.timedelta(days=365)

        return Transaction.objects.filter(
            date__range=[d.strftime("%Y-%m-%d") for d in [start_date, now]]
        )


class ExplicitFieldsModel(models.Model):
    class Meta:
        abstract = True

    def include(self):
        fields_to_include = [f.name for f in self._meta.get_fields()]
        return fields_to_include

    def get_fields(self):
        return {
            f.verbose_name: self.__dict__[f.name]
            for f in self._meta.get_fields()
            if f.name in self.include()
        }


class Bank(ExplicitFieldsModel):
    name = models.CharField('Name', unique=True, max_length=255)
    date_col_name = models.CharField('Date Header', max_length=255)
    amt_col_name = models.CharField('Amount Header', max_length=255)
    desc_col_name = models.CharField('Description Header', max_length=255)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budget:bank-detail', kwargs={'pk': self.pk})

    def include(self):
        return ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']


class AccountHolder(models.Model):
    name = models.CharField('Name', max_length=255, unique=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budget:accountholder-detail', kwargs={'pk': self.pk})


class Account(models.Model):
    name = models.CharField('Name', unique=True, max_length=255)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)
    holder = models.ForeignKey(AccountHolder, to_field='name',
                               on_delete=models.CASCADE, null=True)
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
        return reverse('budget:account-detail', kwargs={'pk': self.pk})

    def min_pay(self, bal=None):
        if bal is None:
            bal = self.balance
        return max(self.min_pay_dlr, self.min_pay_pct / 100 * bal)

    def forecast_next(self, bal=None):
        if bal is None:
            bal = self.balance
        return max(bal * (1 + self.interest_rate / 100 / 12)
                   - self.min_pay(bal=bal), 0)


class Statement(models.Model):
    account = models.ForeignKey(Account, to_field='name', on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField('Year', default=0)
    month = models.PositiveSmallIntegerField('Month', default=0)
    balance = models.DecimalField('Balance', decimal_places=2, max_digits=9)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('account', 'year', 'month')

    def __str__(self):
        return f"{self.date.strftime('%b %Y')}: {self.balance}"

    def get_absolute_url(self):
        return reverse('budget:statement-update', kwargs={'pk': self.pk})

    @property
    def date(self):
        return datetime.date(year=self.year, month=self.month, day=1)


class Upload(models.Model):
    upload_time = models.DateTimeField('Uploaded', auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, to_field='name')
    csv = models.FileField(upload_to='csvs')

    def __str__(self):
        return f"{self.upload_time.strftime('%Y-%m-%d %H:%M:%S (UTC)')} - {self.account}"

    def get_absolute_url(self):
        return reverse('budget:upload-detail', kwargs={'pk': self.pk})

    def parse_transactions(self):
        # TODO: catch all the errors
        # Parse csv
        columns = [
            self.account.bank.date_col_name,
            self.account.bank.amt_col_name,
            self.account.bank.desc_col_name
        ]

        df = pd.read_csv(self.csv, parse_dates=[columns[0]], infer_datetime_format=True)
        df.columns = [c.strip() for c in df.columns]
        df = df[columns]

        # Create transaction objects
        for i, r in df.iterrows():
            t = Transaction(
                upload_id=self,
                account=Account.objects.get(name=self.account_id),
                date=r[columns[0]],
                amount=r[columns[1]],
                description=r[columns[2]]
            )
            try:
                t.save()
            except IntegrityError:
                continue

        # Classify
        for p in Pattern.objects.all():
            p.match_transactions()

        return True


class Category(models.Model):
    name = models.CharField('Name', unique=True, max_length=255)
    budget = models.DecimalField('Monthly Target', decimal_places=2, max_digits=9, default=0.)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budget:category-detail', kwargs={'pk': self.pk})


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, to_field='name')
    name = models.CharField('Name', unique=True, max_length=255)

    class Meta:
        ordering = ['category_id', 'name']

    def __str__(self):
        return f"{self.category_id}/{self.name}"

    def get_absolute_url(self):
        return reverse('budget:subcategory-detail', kwargs={'pk': self.pk})


class Pattern(models.Model):
    pattern = models.CharField('Match Pattern', unique=True, max_length=255)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, to_field='name')

    def __str__(self):
        return self.pattern

    @property
    def category(self):
        return self.subcategory.category

    def get_absolute_url(self):
        return reverse('budget:pattern-detail', kwargs={'pk': self.pk})

    def match_transactions(self):
        Transaction.objects.filter(
            description__iregex=self.pattern,
            category=None
        ).update(
            pattern_id=self.pattern,
            category_id=self.category,
            subcategory_id=self.subcategory_id
        )


class Transaction(models.Model):
    upload_id = models.ForeignKey(Upload, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, to_field='name')
    date = models.DateField('Transaction Date')
    amount = models.DecimalField('Amount', decimal_places=2, max_digits=9)
    description = models.TextField('Description')
    pattern = models.ForeignKey(Pattern, on_delete=models.SET_NULL, null=True, to_field='pattern')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, to_field='name')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, to_field='name')
    objects = TransactionManager()

    class Meta:
        ordering = ['-date']
        unique_together = ('account', 'date', 'amount', 'description')

    def __str__(self):
        return f"{self.account} | {self.date} | {self.amount} | {self.description}"

    def get_absolute_url(self):
        return reverse('budget:transaction-detail', kwargs={'pk': self.pk})
