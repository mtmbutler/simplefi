import datetime
import os
from typing import TYPE_CHECKING

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.db import transaction
from model_mommy import mommy

from budget.tests.utils import login

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client


DAYS_PER_YEAR = 365


class TestMethods:
    def test_upload_parse_transactions_clean(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model('budget.Account')
        Upload = apps.get_model('budget.Upload')
        acc = mommy.make(
            Account, user=user, date_col_name='date', amt_col_name='amt',
            desc_col_name='desc')

        # Make a fake csv
        df = pd.DataFrame(dict(
            date=['2018-11-10', '2018-11-11'],
            amt=[5.54, 3.99],
            desc=['Eggs', 'Spam']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        result = ul.parse_transactions()
        assert result == 'success'
        assert ul.num_transactions == 2
        assert acc.num_transactions == 2

        # Cleanup
        os.remove(temp_path)

    def test_upload_parse_transactions_wrong_header(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model('budget.Account')
        Upload = apps.get_model('budget.Upload')
        acc = mommy.make(
            Account, user=user, date_col_name='date', amt_col_name='amt',
            desc_col_name='desc')

        # Make a fake csv
        df = pd.DataFrame(dict(
            date=['2018-11-10', '2018-11-11'],
            bad_amt_col_name=[5.54, 3.99],
            desc=['Eggs', 'Spam']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        result = ul.parse_transactions()
        assert 'Not all specified columns' in result
        assert acc.num_transactions == 0

        # Cleanup
        os.remove(temp_path)

    def test_upload_parse_transactions_bad_date_format(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model('budget.Account')
        Upload = apps.get_model('budget.Upload')
        acc = mommy.make(
            Account, user=user, date_col_name='date', amt_col_name='amt',
            desc_col_name='desc')

        # Make a fake csv
        df = pd.DataFrame(dict(
            date=['2018-11-100', '2018-11-11'],
            amt=[5.54, 3.99],
            desc=['Eggs', 'Spam']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        with transaction.atomic():
            result = ul.parse_transactions()
        assert 'invalid date format' in result
        assert acc.num_transactions == 0

        # Cleanup
        os.remove(temp_path)

    def test_upload_parse_transactions_str_in_value_col(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model('budget.Account')
        Upload = apps.get_model('budget.Upload')
        acc = mommy.make(
            Account, user=user, date_col_name='date', amt_col_name='amt',
            desc_col_name='desc')

        # Make a fake csv
        df = pd.DataFrame(dict(
            date=['2018-11-10', '2018-11-11'],
            amt=['five dollars', 3.99],
            desc=['Eggs', 'Spam']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        with transaction.atomic():
            result = ul.parse_transactions()
        assert 'Validation error' in result
        assert acc.num_transactions == 0

        # Cleanup
        os.remove(temp_path)

    def test_pattern_match_transactions(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        user = login(client, django_user_model)
        Pattern = apps.get_model('budget.Pattern')
        Transaction = apps.get_model('budget.Transaction')
        assert Pattern.objects.count() == 0
        assert Transaction.objects.count() == 0

        # Create the pattern and transactions
        p = mommy.make(Pattern, user=user, pattern=r'.*wal[- ]?mart.*')
        shared_kwargs = dict(_model=Transaction, user=user, pattern=None)
        mommy.make(**shared_kwargs, id=1, description='WalMart')           # Yes
        mommy.make(**shared_kwargs, id=2, description='Wal Mart')          # Yes
        mommy.make(**shared_kwargs, id=3, description='WallMart')          # No
        mommy.make(**shared_kwargs, id=4, description='Target')            # No
        mommy.make(**shared_kwargs, id=5, description='Debit - Wal-Mart')  # Yes

        # Validate matches
        p.match_transactions()
        assert [t.id for t in p.transaction_set.all()] == [1, 2, 5]


class TestManagers:
    def test_thirteen_months_manager(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        model = 'budget.Transaction'
        today = datetime.date.today()
        two_years_ago = today - datetime.timedelta(days=2 * DAYS_PER_YEAR)
        user = login(client, django_user_model)

        # Make objects
        old_trans = mommy.make(model, date=two_years_ago, user=user)
        new_trans = mommy.make(model, date=today, user=user)
        old_trans.save()
        new_trans.save()

        # Test
        Transaction = apps.get_model(model)
        qs = Transaction.objects.in_last_thirteen_months(user)
        assert new_trans in qs and old_trans not in qs
