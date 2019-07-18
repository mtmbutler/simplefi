import csv
import datetime
import os
from typing import Dict, TYPE_CHECKING

import pandas as pd
from django.conf import settings
from django.db import models, IntegrityError
from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.urls import reverse
from django.utils import timezone

from budget.utils import thirteen_months_ago

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import Model
    from django.db.models.query import QuerySet


class TransactionManager(models.Manager):
    @staticmethod
    def in_last_thirteen_months(user: 'User', **kwargs) -> 'QuerySet':
        return Transaction.objects.filter(
            user=user,
            date__range=[
                d.strftime("%Y-%m-%d")
                for d in [thirteen_months_ago(), timezone.now()]],
            **kwargs)


class UserDataModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Account(UserDataModel):
    name = models.CharField('Name', max_length=255)
    date_col_name = models.CharField('Date Header', max_length=255)
    amt_col_name = models.CharField('Amount Header', max_length=255)
    desc_col_name = models.CharField('Description Header', max_length=255)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('budget:account-detail', kwargs={'pk': self.pk})

    @property
    def transaction_set(self) -> 'QuerySet':
        return Transaction.objects.filter(upload__account=self)

    @property
    def num_transactions(self) -> int:
        return self.transaction_set.count()


class Upload(UserDataModel):
    SUCCESS_CODE = 'success'

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

    def get_absolute_url(self) -> str:
        return reverse('budget:upload-detail', kwargs={'pk': self.pk})

    @property
    def num_transactions(self) -> int:
        return self.transaction_set.count()

    def parse_transactions(self) -> str:
        # Parse csv
        columns = [
            self.account.date_col_name,
            self.account.amt_col_name,
            self.account.desc_col_name
        ]

        try:
            df = pd.read_csv(
                self.csv, parse_dates=[columns[0]], infer_datetime_format=True)
        except ValueError as e:
            return str(e)
        df.columns = [c.strip() for c in df.columns]
        try:
            df = df[columns]
        except KeyError:
            return (f"Not all specified columns {columns} found in CSV"
                    f" header {list(df.columns)}")

        # Create transaction objects
        err = None
        for i, r in df.iterrows():
            t = Transaction(
                user=self.user,
                upload=self,
                date=r[columns[0]],
                amount=r[columns[1]],
                description=r[columns[2]])
            try:
                t.save()
            except (IntegrityError, ValidationError) as e:
                if isinstance(e, ValidationError):
                    err = f"Validation error: {e}"
                    break
                continue

        if err:
            return err

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

        return self.SUCCESS_CODE


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

    def transactions(self, user) -> 'QuerySet':
        return Transaction.objects.filter(
            user=user, pattern__category__class_field=self)

    def get_absolute_url(self) -> str:
        return reverse('budget:class-detail', kwargs={'pk': self.pk})


class Budget(UserDataModel):
    class_field = models.ForeignKey(TransactionClass, on_delete=models.CASCADE)
    value = models.DecimalField('Amount', decimal_places=2, max_digits=9)

    class Meta:
        unique_together = ('user', 'class_field')

    def __str__(self):
        return f"{self.class_field} - {self.value}"

    @property
    def num_class_transactions(self) -> int:
        return self.class_field.transactions(user=self.user).count()

    @property
    def fmt_value(self) -> str:
        return f'{self.value:,.2f}'

    def get_absolute_url(self) -> str:
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

    def get_absolute_url(self) -> str:
        return reverse('budget:category-detail', kwargs={'pk': self.pk})

    @property
    def num_transactions(self) -> int:
        return self.transaction_set.count()

    @property
    def transaction_set(self) -> 'QuerySet':
        return Transaction.objects.filter(pattern__category=self)


class Pattern(UserDataModel):
    pattern = models.CharField('Match Pattern', max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)

    class Meta:
        unique_together = ('user', 'pattern')

    def __str__(self):
        return self.pattern

    @property
    def class_field(self) -> 'TransactionClass':
        return self.category.class_field

    @property
    def num_transactions(self) -> int:
        return self.transaction_set.count()

    def get_absolute_url(self) -> str:
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

    def get_absolute_url(self) -> str:
        return reverse('budget:transaction-detail', kwargs={'pk': self.pk})

    @property
    def class_field(self) -> 'TransactionClass':
        return self.pattern.class_field

    @property
    def category(self) -> 'Category':
        return self.pattern.category

    @property
    def account(self) -> 'Account':
        return self.upload.account

    @property
    def fmt_amt(self) -> str:
        return f'{self.amount:,.2f}'

    @property
    def trunc_desc(self) -> str:
        if len(self.description) <= self.DESC_TRUNC_LEN:
            return self.description
        else:
            return self.description[:self.DESC_TRUNC_LEN] + '...'


class CSVBackup(UserDataModel):
    NO_CSV_MSG = "No CSV associated with selected backup."
    BACKUP_FIELDS = ['Account', 'Class', 'Category',
                     'Date', 'Amount', 'Description']

    creation_time = models.DateTimeField('Created', auto_now_add=True)
    csv = models.FileField('CSV', upload_to='csvs', null=True)

    def __str__(self):
        return self.creation_time.strftime('%Y-%m-%d %H:%M:%S')

    def get_absolute_url(self) -> str:
        return reverse('budget:backup-detail', kwargs={'pk': self.pk})

    def create_backup(self):
        """Saves all user transactions to a CSV FileField.

        Includes account name, class name, and category name in addition
        to the base model fields.
        """
        qs = Transaction.objects.filter(
            user=self.user
        ).order_by('upload__account', 'date')

        # Create the CSV
        now = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
        path = os.path.join(settings.MEDIA_ROOT, 'csvs', f'transactions_{now}.csv')
        with open(path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=self.BACKUP_FIELDS)
            writer.writeheader()
            for t in qs.all():
                writer.writerow({
                    'Account': t.account.name,
                    'Class': t.class_field.name.title(),
                    'Category': t.category.name,
                    'Date': t.date.strftime('%Y-%m-%d'),
                    'Amount': str(t.amount),
                    'Description': t.description})

        self.csv.name = path
        self.save()

    def file_response(self) -> 'FileResponse':
        """Serves up the CSV as a download."""
        if self.csv is None:
            now = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
            path = os.path.join(settings.MEDIA_ROOT, f'error_{now}.txt')
            with open(path, 'w') as f:
                f.write(self.NO_CSV_MSG)
            return FileResponse(open(path, 'rb'), as_attachment=True)
        return FileResponse(self.csv, as_attachment=True)

    def restore(self) -> str:
        """Restores the user's database from the CSV.

        First, identifies any accounts that aren't already in the
        database, and creates them. Second, creates an upload for each
        account to associate with the transactions. Then, parses through
        all the transactions and adds them to the DB.

        Categories from the backup CSV are just for user convenience if
        they want to do their own analysis -- they're not used on
        re-upload. Instead, the user's patterns are used to re-assign
        the categories, just as with a normal CSV upload.

        Returns a status message.
        """
        if self.csv is None:
            return self.NO_CSV_MSG

        # Read CSV
        try:
            df = pd.read_csv(
                self.csv.path, usecols=self.BACKUP_FIELDS,
                infer_datetime_format=True)
        except ValueError as e:
            return str(e)

        # Build dict of accounts, creating new ones as needed
        accounts = {}  # type: Dict[str, Account]
        for acc_name in df['Account'].unique():
            acc_obj, __ = Account.objects.get_or_create(
                user=self.user, name=acc_name,
                defaults=dict(date_col_name='Date',
                              amt_col_name='Amount',
                              desc_col_name='Description'))
            accounts['acc_name'] = acc_obj

        # Create new uploads to associate with each account
        uploads = {}  # type: Dict[str, Upload]
        for acc_name, account in accounts.items():
            uploads[acc_name] = Upload(user=self.user, account=account,
                                       csv=self.csv)
        Upload.objects.bulk_create(uploads.values())

        # Iterate through transactions
        err = None
        for __, r in df.iterrows():
            t = Transaction(
                user=self.user,
                upload=uploads[r['Account']],
                date=r['Date'],
                amount=r['Amount'],
                description=r['Description'],
                pattern=None)
            try:
                t.save()
            except (IntegrityError, ValidationError) as e:
                if isinstance(e, ValidationError):
                    err = f"Validation error: {e}"
                    break
                continue

        if err:
            return err

        # Classify
        patterns = (
            Pattern.objects
            .filter(user=self.user)
            .annotate(matches=models.Count('transaction'))
            .order_by('-matches'))  # Start with most-used patterns
        for p in patterns:
            p.match_transactions()

        return Upload.SUCCESS_CODE
