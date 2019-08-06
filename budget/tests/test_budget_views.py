import datetime
import math
import os
import random
import string
from typing import Type, TYPE_CHECKING

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from model_mommy import mommy

from budget.tests.utils import login

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client

    from budget import models

TEST_NAME = 'Scooby Doo'
RAND_FILE_NAME_LENGTH = 20
TEMP_DIR = 'tmp'


def hr(response):
    return str(response.content).replace('\\n', '\n')


def create_recursive_dependencies(model_obj):
    for f in model_obj._meta.fields:
        if f.name == 'user' or not isinstance(f, models.ForeignKey):
            continue
        o = mommy.make(f.related_model)
        o = create_recursive_dependencies(o)
        o.save()
        setattr(model_obj, f.name, o)

    return model_obj


def parent_obj_set(parent_models):
    d = {}
    for k in parent_models:
        klass = mommy.make(k)
        klass = create_recursive_dependencies(klass)
        klass.save()
        d[k] = klass
    return d


def today_str():
    return timezone.now().strftime('%Y-%m-%d')


def rand_str(n):
    return ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for __ in range(n))


def temp_file(content=''):
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    path = os.path.join(TEMP_DIR, rand_str(RAND_FILE_NAME_LENGTH) + '.txt')
    if not content:
        content = rand_str(RAND_FILE_NAME_LENGTH)
    with open(path, 'w') as f:
        f.write(content)
    return path


class TestPatternClassificationViews:
    def test_classify_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        url = 'budget:classify'

        # Setup
        user = login(client, django_user_model)
        pat_model = apps.get_model('budget.Pattern')     # type: Type[models.Pattern]
        tr_model = apps.get_model('budget.Transaction')  # type: Type[models.Transaction]
        assert pat_model.objects.count() == 0
        assert tr_model.objects.count() == 0

        # Make some transactions and a pattern
        for i in range(3):
            mommy.make(tr_model, user=user,
                       description=f'transaction {i}',
                       pattern=None)  # type: models.Transaction
        assert tr_model.objects.count() == 3
        pat = mommy.make(pat_model, user=user,
                         pattern='transaction.*')  # type: models.Pattern
        assert pat_model.objects.count() == 1

        # GET the view and check that the pattern associated
        r = client.get(reverse(url))
        assert r.status_code == 302
        assert pat.num_transactions == 3

    def test_declassify_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        url = 'budget:declassify'

        # Setup
        user = login(client, django_user_model)
        pat_model = apps.get_model('budget.Pattern')     # type: Type[models.Pattern]
        tr_model = apps.get_model('budget.Transaction')  # type: Type[models.Transaction]
        assert pat_model.objects.count() == 0
        assert tr_model.objects.count() == 0

        # Make some transactions and a pattern
        pat = mommy.make(pat_model, user=user,
                         pattern='transaction.*')  # type: models.Pattern
        assert pat_model.objects.count() == 1
        for i in range(3):
            mommy.make(tr_model, user=user,
                       description=f'transaction {i}',
                       pattern=pat)  # type: models.Transaction
        assert tr_model.objects.count() == 3
        assert pat.num_transactions == 3

        # GET the view and check that the pattern de-associated
        r = client.get(reverse(url))
        assert r.status_code == 302
        assert pat.num_transactions == 0


class TestPatternBulkUpdateView:
    def test_bulk_update_invalid_csv(self, client, django_user_model):
        url = reverse('budget:pattern-bulk-update')
        login(client, django_user_model)
        pattern_model = apps.get_model('budget.Pattern')
        assert pattern_model.objects.count() == 0

        # Create the CSV
        df = pd.DataFrame(dict(
            Pattern=['.*state.*farm.*', '.*target.*'],
            Category=['Insurance', 'Shopping'],
            BadColumnName=['Bills', 'Discretionary']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        try:
            with open(temp_path, 'rb') as f:
                r = client.post(url, {'csv': f})
            assert r.status_code == 200
            assert pattern_model.objects.count() == 0
            assert "columns expected but not found" in hr(r)

        finally:
            os.remove(temp_path)

    def test_bulk_update_valid(self, client, django_user_model):
        url = reverse('budget:pattern-bulk-update')
        login(client, django_user_model)
        cat_model = apps.get_model('budget.Category')
        pattern_model = apps.get_model('budget.Pattern')
        assert pattern_model.objects.count() == 0

        # Create the transaction class objects
        mommy.make('budget.TransactionClass', name='bills')
        mommy.make('budget.TransactionClass', name='discretionary')

        # Create the CSV
        df = pd.DataFrame(dict(
            Pattern=['.*state.*farm.*', '.*target.*'],
            Category=['Insurance', 'Shopping'],
            Class=['Bills', 'Discretionary']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        try:
            with open(temp_path, 'rb') as f:
                r = client.post(url, {'csv': f})
            assert r.status_code == 302
            assert cat_model.objects.count() == 2
            assert pattern_model.objects.count() == 2

        finally:
            os.remove(temp_path)


class TestBackupViews:
    def test_backup_create_new_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        url = 'budget:backup-addnew'

        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model('budget.CSVBackup')  # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0

        # Make some transactions
        tr_model = apps.get_model('budget.Transaction')  # type: Type[models.Transaction]
        assert tr_model.objects.count() == 0
        mommy.make(tr_model, user=user, amount=5.54)
        mommy.make(tr_model, user=user, amount=3.99)
        assert tr_model.objects.count() == 2

        # POST to the page
        r = client.post(reverse(url))
        assert r.status_code == 302
        assert bak_model.objects.count() == 1
        obj = bak_model.objects.first()  # type: models.CSVBackup

        try:
            # Check that the transactions are in the CSV
            df = pd.read_csv(obj.csv)
            assert df.shape == (2, 6)
            assert math.isclose(df['Amount'].sum(), 9.53, rel_tol=1e-9, abs_tol=0.0)

        finally:
            os.remove(obj.csv.path)

    def test_backup_purge_confirm_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        url = 'budget:backup-purge-confirm'
        template = 'budget/backup-purge-confirm.html'
        login(client, django_user_model)
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_backup_purge_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        url = 'budget:backup-purge'

        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model('budget.CSVBackup')  # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0

        # Make some transactions
        tr_model = apps.get_model('budget.Transaction')  # type: Type[models.Transaction]
        assert tr_model.objects.count() == 0
        mommy.make(tr_model, user=user, amount=5.54)
        mommy.make(tr_model, user=user, amount=3.99)
        assert tr_model.objects.count() == 2

        # POST to the page
        r = client.post(reverse(url))
        assert r.status_code == 302
        assert tr_model.objects.count() == 0

    def test_backup_download_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        url = 'budget:backup-download'
        user = login(client, django_user_model)
        bak_model = apps.get_model('budget.CSVBackup')   # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0

        # Make a fake file
        s = 'foo bar baz spam ham eggs'
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.txt')
        with open(temp_path, 'w') as f:
            f.write(s)

        try:
            bak = mommy.make(bak_model, user=user, csv=temp_path)
            assert bak_model.objects.count() == 1
            r = client.get(reverse(url, kwargs={'pk': bak.pk}))
            text = ''.join(line.decode('UTF-8')
                           for line in r.streaming_content)
            assert text == s

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_restore_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        url = 'budget:backup-restore'
        user = login(client, django_user_model)
        bak_model = apps.get_model('budget.CSVBackup')   # type: Type[models.CSVBackup]
        tr_model = apps.get_model('budget.Transaction')  # type: Type[models.Transaction]
        acc_model = apps.get_model('budget.Account')     # type: Type[models.Account]
        ul_model = apps.get_model('budget.Upload')       # type: Type[models.Upload]
        for model in (bak_model, tr_model, acc_model, ul_model):
            assert model.objects.count() == 0

        # Make a fake csv
        df = pd.DataFrame(dict(
            Account=['Checking', 'Checking'],
            Class=['', ''],
            Category=['', ''],
            Date=['2018-11-10', '2018-11-11'],
            Amount=[5.54, 3.99],
            Description=['Eggs', 'Spam']))
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp.csv')
        df.to_csv(temp_path)

        try:
            # Create the backup object and restore
            bak = mommy.make(bak_model, user=user, csv=temp_path)
            r = client.post(reverse(url, kwargs={'pk': bak.pk}))
            assert r.status_code == 302

            # There should now be two transactions attached to one
            # upload and one account, and msg should be a success code
            assert tr_model.objects.count() == 2
            assert float(tr_model.objects.aggregate(
                models.Sum('amount'))['amount__sum']) == 9.53
            assert acc_model.objects.count() == 1
            assert acc_model.objects.first().name == 'Checking'
            assert acc_model.objects.first().num_transactions == 2
            assert ul_model.objects.count() == 1
            assert ul_model.objects.first().account.name == 'Checking'
            assert ul_model.objects.first().num_transactions == 2

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_failed_restore_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        url = 'budget:backup-restore'
        user = login(client, django_user_model)
        bak_model = apps.get_model('budget.CSVBackup')   # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0

        # Create the backup object w/ no CSV and try to restore
        bak = mommy.make(bak_model, user=user, csv=None)
        r = client.post(reverse(url, kwargs={'pk': bak.pk}))
        msgs = r.cookies['messages'].value
        assert r.status_code == 302
        assert 'Restore failed: No CSV associated' in msgs


class TestIndexView:
    def test_index_no_data(self, client, django_user_model):
        url = 'budget:index'
        template = 'budget/index.html'

        login(client, django_user_model)

        # Check the page
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_index_with_data(self, client, django_user_model):
        url = 'budget:index'
        template = 'budget/index.html'

        user = login(client, django_user_model)
        cls = mommy.make('budget.TransactionClass', name='Bills')
        cat = mommy.make('budget.Category', class_field=cls, user=user)
        ptrn = mommy.make('budget.Pattern', user=user, category=cat)
        mommy.make('budget.Budget', class_field=cls, user=user)
        for __ in range(10):
            mommy.make('budget.Transaction', user=user, pattern=ptrn)

        # Check the page
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_index_no_budget(self, client, django_user_model):
        url = 'budget:index'
        template = 'budget/index.html'

        user = login(client, django_user_model)
        cls = mommy.make('budget.TransactionClass', name='Bills')
        cat = mommy.make('budget.Category', class_field=cls, user=user)
        ptrn = mommy.make('budget.Pattern', user=user, category=cat)
        for __ in range(10):
            mommy.make('budget.Transaction', user=user, pattern=ptrn)

        # Check the page
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names


class TestDetailViews:
    @staticmethod
    def detail_view_test(client, django_user_model, model, viewname,
                         user_required=True, search_str='', obj_params=None):
        if obj_params is None:
            obj_params = dict()
        user = login(client, django_user_model)
        if user_required:
            obj_params.update(user=user)

        obj = mommy.make(model, **obj_params)
        obj = create_recursive_dependencies(obj)

        obj.save()
        response = client.get(
            reverse(viewname, kwargs={'pk': obj.id}))

        assert response.status_code == 200 and search_str in hr(response)

    def test_account_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.Account',
            'budget:account-detail', search_str=TEST_NAME,
            obj_params={'name': TEST_NAME})

    def test_upload_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.Upload',
            'budget:upload-detail',
            obj_params={'_create_files': True})

    def test_class_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.TransactionClass',
            'budget:class-detail', user_required=False)

    def test_category_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.Category',
            'budget:category-detail', search_str=TEST_NAME,
            obj_params={'name': TEST_NAME})

    def test_pattern_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.Pattern',
            'budget:pattern-detail', search_str=TEST_NAME,
            obj_params={'pattern': TEST_NAME})

    def test_transaction_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.Transaction',
            'budget:transaction-detail', search_str=TEST_NAME,
            obj_params={'description': TEST_NAME})

    def test_backup_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.CSVBackup',
            'budget:backup-detail',
            obj_params={'_create_files': True})


class TestListViews:
    @staticmethod
    def list_view_test(client, django_user_model, url, template):
        login(client, django_user_model)
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_account_list_view(self, client, django_user_model):
        url = 'budget:account-list'
        template = 'budget/account-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_pattern_list_view(self, client, django_user_model):
        url = 'budget:pattern-list'
        template = 'budget/pattern-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_transaction_list_view(self, client, django_user_model):
        url = 'budget:transaction-list'
        template = 'budget/transaction-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_upload_list_view(self, client, django_user_model):
        url = 'budget:upload-list'
        template = 'budget/upload-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_backup_list_view(self, client, django_user_model):
        url = 'budget:backup-list'
        template = 'budget/backup-list.html'
        self.list_view_test(client, django_user_model, url, template)


class TestCreateViews:
    @staticmethod
    def create_view_test(client, model, url, template, user,
                         user_required=True, obj_params=None,
                         file_field=None):
        # Make sure there are no existing objects
        model_cls = apps.get_model(*model.split('.'))
        model_cls.objects.all().delete()
        assert model_cls.objects.count() == 0

        # Check the create page
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

        # Use the create page to create obj and assert success
        if file_field:
            with open(obj_params[file_field]) as f:
                d = dict(obj_params)
                d.update({file_field: f})
                response = client.post(reverse(url), data=d)
        else:
            response = client.post(reverse(url), data=obj_params)
        try:
            assert (
                response.status_code == 302
                and model_cls.objects.count() == 1)
            if user_required:
                obj = model_cls.objects.first()
                assert obj.user == user
        except AssertionError:
            print(hr(response))
            raise

    def test_account_create_view(self, client, django_user_model):
        url = 'budget:account-add'
        model = 'budget.Account'
        template = 'budget/account-add.html'
        user = login(client, django_user_model)

        obj_params = dict(
            name='TestObj', date_col_name='Date', amt_col_name='Amt',
            desc_col_name='Desc')

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)

    def test_category_create_view(self, client, django_user_model):
        url = 'budget:category-add'
        model = 'budget.Category'
        template = 'budget/category-add.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['budget.TransactionClass']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            name='TestObj', class_field=parents['budget.TransactionClass'].id)

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)

    def test_pattern_create_view(self, client, django_user_model):
        url = 'budget:pattern-add'
        model = 'budget.Pattern'
        template = 'budget/pattern-add.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['budget.Category']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            pattern='TestObj', category=parents['budget.Category'].id)

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)

    def test_upload_create_view(self, client, django_user_model):
        url = 'budget:upload-add'
        model = 'budget.Upload'
        template = 'budget/upload-add.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['budget.Account']
        parents = parent_obj_set(parent_models)

        # Create file
        acc = parents['budget.Account']
        content = ','.join(
            [acc.date_col_name, acc.amt_col_name, acc.desc_col_name])
        csv = temp_file(content=content)
        try:
            obj_params = dict(
                upload_time=today_str(), account=acc.id, csv=csv)

            self.create_view_test(
                client, model, url, template, user,
                obj_params=obj_params, file_field='csv')

        finally:
            os.remove(csv)

    def test_failed_upload_create_view(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        # Setup
        url = 'budget:upload-add'
        user = login(client, django_user_model)
        acc_model = apps.get_model('budget.Account')  # type: Type[models.Account]
        ul_model = apps.get_model('budget.Upload')    # type: Type[models.Upload]
        assert acc_model.objects.count() == 0
        acc = mommy.make(acc_model, user=user)
        assert acc_model.objects.count() == 1
        assert ul_model.objects.count() == 0
        csv = temp_file()  # Not a valid backup CSV

        try:
            # Try to create the upload object
            with open(csv) as f:
                r = client.post(reverse(url), data=dict(account=acc.id, csv=f))
            print(r.__dict__)
            msgs = r.cookies['messages'].value
            assert r.status_code == 302
            assert 'Upload failed:' in msgs
            assert ul_model.objects.count() == 0
        finally:
            os.remove(csv)

    def test_backup_create_view(self, client, django_user_model):
        url = 'budget:backup-add'
        model = 'budget.CSVBackup'
        template = 'budget/backup-add.html'
        user = login(client, django_user_model)

        # Create file
        content = ','.join(
            ['Account', 'Class', 'Category',
             'Date', 'Amount', 'Description'])
        csv = temp_file(content=content)

        try:
            obj_params = dict(creation_time=today_str(), csv=csv)

            self.create_view_test(
                client, model, url, template, user,
                obj_params=obj_params, file_field='csv')
        finally:
            os.remove(csv)


class TestUpdateViews:
    @staticmethod
    def update_view_test(client, model, url, template, user,
                         user_required=True, obj_params=None,
                         create_recursive=True):
        # Make sure there are no existing objects and make a new one
        model_cls = apps.get_model(*model.split('.'))
        model_cls.objects.all().delete()
        assert model_cls.objects.count() == 0
        create_kwargs = dict(_model=model)
        if user_required:
            create_kwargs.update(user=user)
        obj = mommy.make(**create_kwargs)
        if create_recursive:
            create_recursive_dependencies(obj)
        obj.save()

        # Check the update page
        response = client.get(reverse(url, kwargs={'pk': obj.pk}))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

        # Use the update page to update obj and assert success
        response = client.post(reverse(url, kwargs={'pk': obj.pk}), data=obj_params)
        try:
            assert response.status_code == 302
            obj = model_cls.objects.first()
            for k, v in obj_params.items():
                actual_val = getattr(obj, k)
                if isinstance(actual_val, datetime.date):
                    actual_val = actual_val.strftime('%Y-%m-%d')
                if not isinstance(actual_val, models.Model):
                    assert actual_val == v
            if user_required:
                assert obj.user == user
        except AssertionError:
            print(hr(response))
            raise

    def test_account_update_view(self, client, django_user_model):
        url = 'budget:account-update'
        model = 'budget.Account'
        template = 'budget/account-update.html'
        user = login(client, django_user_model)

        obj_params = dict(
            name='TestObj', date_col_name='Date', amt_col_name='Amt',
            desc_col_name='Desc')

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)

    def test_category_update_view(self, client, django_user_model):
        url = 'budget:category-update'
        model = 'budget.Category'
        template = 'budget/category-update.html'
        user = login(client, django_user_model)

        # Parents
        # parent_models = ['budget.TransactionClass']
        # parents = parent_obj_set(parent_models)

        obj_params = dict(
            name='TestObj', class_field=1)

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)

    def test_pattern_update_view(self, client, django_user_model):
        url = 'budget:pattern-update'
        model = 'budget.Pattern'
        template = 'budget/pattern-update.html'
        user = login(client, django_user_model)

        obj_params = dict(
            pattern='TestObj', category=1)

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)

    def test_budget_update_view(self, client, django_user_model):
        url = 'budget:budget-update'
        model = 'budget.Budget'
        template = 'budget/budget-update.html'
        user = login(client, django_user_model)

        obj_params = dict(
            class_field=1,
            value=1000)

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params,
            create_recursive=False)


class TestDeleteViews:
    @staticmethod
    def delete_view_test(client, django_user_model, model, url,
                         user_required=True, obj_params=None):
        # Make sure there are no existing objects
        model_cls = apps.get_model(*model.split('.'))
        model_cls.objects.all().delete()
        assert model_cls.objects.count() == 0

        # Create the object and assert success
        if obj_params is None:
            obj_params = dict()
        user = login(client, django_user_model)
        if user_required:
            obj_params.update(user=user)
        obj = mommy.make(model, **obj_params)
        obj = create_recursive_dependencies(obj)
        obj.save()
        assert model_cls.objects.count() == 1

        # Check the delete page
        response = client.get(reverse(url, kwargs={'pk': obj.id}))
        assert (
            response.status_code == 200
            and model_cls.objects.count() == 1)

        # Delete the object and verify
        response = client.post(reverse(url, kwargs={'pk': obj.id}))
        assert (
            response.status_code == 302
            and model_cls.objects.count() == 0)

    def test_account_delete_view(self, client, django_user_model):
        model = 'budget.Account'
        url = 'budget:account-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_category_delete_view(self, client, django_user_model):
        model = 'budget.Category'
        url = 'budget:category-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_pattern_delete_view(self, client, django_user_model):
        model = 'budget.Pattern'
        url = 'budget:pattern-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_transaction_delete_view(self, client, django_user_model):
        model = 'budget.Transaction'
        url = 'budget:transaction-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_upload_delete_view(self, client, django_user_model):
        model = 'budget.Upload'
        url = 'budget:upload-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_backup_delete_view(self, client, django_user_model):
        model = 'budget.CSVBackup'
        url = 'budget:backup-delete'
        self.delete_view_test(client, django_user_model, model, url)
