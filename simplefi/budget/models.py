import datetime
import locale

import pandas as pd
from django.conf import settings
from django.db import models, IntegrityError
from django.urls import reverse
from django.utils import timezone

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


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


class Account(UserDataModel):
    name = models.CharField('Name', max_length=255)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('budget:account-detail', kwargs={'pk': self.pk})

    @property
    def transaction_set(self):
        return Transaction.objects.filter(upload__account=self)


class Upload(UserDataModel):
    upload_time = models.DateTimeField('Uploaded', auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    csv = models.FileField(upload_to='csvs')

    class Meta:
        ordering = ['-upload_time']

    def __str__(self):
        return (
            self.upload_time
            .astimezone(timezone.get_current_timezone())
            .strftime('%d %b %Y - %-I:%M %p'))

    def get_absolute_url(self):
        return reverse('budget:upload-detail', kwargs={'pk': self.pk})

    @property
    def num_transactions(self):
        return self.transaction_set.count()

    def parse_transactions(self):
        # TODO: catch all the errors
        # Parse csv
        columns = [
            self.account.bank.date_col_name,
            self.account.bank.amt_col_name,
            self.account.bank.desc_col_name
        ]

        try:
            df = pd.read_csv(self.csv, parse_dates=[columns[0]], infer_datetime_format=True)
        except ValueError:
            return  # TODO
        df.columns = [c.strip() for c in df.columns]
        df = df[columns]

        # Create transaction objects
        for i, r in df.iterrows():
            t = Transaction(
                user=self.user,
                upload=self,
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

    @property
    def num_class_transactions(self):
        return self.class_field.transactions(user=self.user).count()

    @property
    def fmt_value(self):
        return locale.currency(self.value, grouping=True)

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
        return self.name

    def get_absolute_url(self):
        return reverse('budget:category-detail', kwargs={'pk': self.pk})

    @property
    def num_transactions(self):
        return self.transaction_set.count()

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

    @property
    def num_transactions(self):
        return self.transaction_set.count()

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
    DESC_TRUNC_LEN = 30

    upload = models.ForeignKey(Upload, on_delete=models.CASCADE)
    date = models.DateField('Transaction date')
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
        return self.upload.account

    @property
    def fmt_amt(self):
        return locale.currency(self.amount, grouping=True)

    @property
    def trunc_desc(self):
        if len(self.description) <= self.DESC_TRUNC_LEN:
            return self.description
        else:
            return self.description[:self.DESC_TRUNC_LEN] + '...'
