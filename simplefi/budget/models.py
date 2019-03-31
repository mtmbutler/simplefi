import datetime

import pandas as pd
from django.conf import settings
from django.db import models, IntegrityError
from django.urls import reverse
from django.utils import timezone


class TransactionManager(models.Manager):
    @staticmethod
    def in_last_thirteen_months(user):
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
            user=user,
            date__range=[d.strftime("%Y-%m-%d") for d in [start_date, now]]
        )


class UserDataModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Bank(UserDataModel):
    name = models.CharField('Name', max_length=255)
    date_col_name = models.CharField('Date Header', max_length=255)
    amt_col_name = models.CharField('Amount Header', max_length=255)
    desc_col_name = models.CharField('Description Header', max_length=255)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budget:bank-detail', kwargs={'pk': self.pk})


class AccountHolder(UserDataModel):
    name = models.CharField('Name', max_length=255)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budget:accountholder-detail', kwargs={'pk': self.pk})


class Account(UserDataModel):
    name = models.CharField('Name', max_length=255)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)
    holder = models.ForeignKey(AccountHolder, on_delete=models.CASCADE,
                               null=True)
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

    @property
    def transaction_set(self):
        return Transaction.objects.filter(upload_id__account=self)


class Statement(UserDataModel):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    year = models.PositiveSmallIntegerField('Year', default=0)
    month = models.PositiveSmallIntegerField('Month', default=0)
    balance = models.DecimalField('Balance', decimal_places=2, max_digits=9)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('user', 'account', 'year', 'month')

    def __str__(self):
        return f"{self.date.strftime('%b %Y')}: {self.balance}"

    def get_absolute_url(self):
        return reverse('budget:statement-update', kwargs={'pk': self.pk})

    @property
    def date(self):
        return datetime.date(year=self.year, month=self.month, day=1)


class Upload(UserDataModel):
    upload_time = models.DateTimeField('Uploaded', auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
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
                user=self.user,
                upload_id=self,
                date=r[columns[0]],
                amount=r[columns[1]],
                description=r[columns[2]]
            )
            try:
                t.save()
            except IntegrityError:
                continue

        # Classify
        patterns = (
            Pattern.objects
            .filter(user=self.user)
            .annotate(matches=models.Count('transaction'))
            .order_by('-matches'))  # Start with most-used patterns
        for p in patterns:
            unmatched = self.transaction_set.filter(pattern=None)
            if not unmatched.exists():
                break
            p.match_transactions()

        return True


class TransactionClass(models.Model):
    CLASSES = (
        ('income', 'Income'),
        ('discretionary', 'Discretionary'),
        ('bills', 'Bills'),
        ('debt', 'Debt'),
        ('savings', 'Savings')
    )
    name = models.CharField('Name', unique=True, max_length=255,
                            choices=CLASSES)

    class Meta:
        verbose_name_plural = "transaction classes"

    def __str__(self):
        return self.get_name_display()

    def transactions(self, user):
        return Transaction.objects.filter(
            user=user, pattern__category__class_field=self)


class Budget(UserDataModel):
    class_field = models.ForeignKey(TransactionClass, on_delete=models.CASCADE)
    value = models.DecimalField('Amount', decimal_places=2, max_digits=9)

    class Meta:
        unique_together = ('user', 'class_field')

    def __str__(self):
        return f"{self.class_field} - {self.value}"

    def get_absolute_url(self):
        return reverse('budget:class-detail', kwargs={'pk': self.class_field_id})


class Category(UserDataModel):
    class_field = models.ForeignKey(TransactionClass, on_delete=models.CASCADE, null=True)
    name = models.CharField('Name', max_length=255)

    class Meta:
        unique_together = ('user', 'class_field', 'name')
        ordering = ['class_field_id', 'name']
        verbose_name_plural = "categories"

    def __str__(self):
        return f"{self.class_field}/{self.name}"

    def get_absolute_url(self):
        return reverse('budget:category-detail', kwargs={'pk': self.pk})

    @property
    def transaction_set(self):
        return Transaction.objects.filter(pattern__category=self)


class Pattern(UserDataModel):
    pattern = models.CharField('Match Pattern', max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)

    class Meta:
        unique_together = ('user', 'pattern')

    def __str__(self):
        return self.pattern

    @property
    def class_field(self):
        return self.category.class_field

    def get_absolute_url(self):
        return reverse('budget:pattern-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.match_transactions()

    def match_transactions(self):
        Transaction.objects.filter(
            user=self.user,
            description__iregex=self.pattern,
            pattern=None
        ).update(pattern=self)


class Transaction(UserDataModel):
    upload_id = models.ForeignKey(Upload, on_delete=models.CASCADE)
    date = models.DateField('Transaction Date')
    amount = models.DecimalField('Amount', decimal_places=2, max_digits=9)
    description = models.TextField('Description')
    pattern = models.ForeignKey(Pattern, on_delete=models.SET_NULL, null=True)

    objects = TransactionManager()

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date', 'amount', 'description')

    def __str__(self):
        return f"{self.account} | {self.date} | {self.amount} | {self.description}"

    def get_absolute_url(self):
        return reverse('budget:transaction-detail', kwargs={'pk': self.pk})

    @property
    def class_field(self):
        return self.pattern.class_field

    @property
    def category(self):
        return self.pattern.category

    @property
    def account(self):
        return self.upload_id.account
