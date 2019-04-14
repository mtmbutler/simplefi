import datetime
import os
import random
import string

from django.apps import apps
from django.db import models
from django.urls import reverse
from django.utils import timezone
from model_mommy import mommy

from budget.tests.utils import login

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


class TestOtherViews:
    def test_index(self, client, django_user_model):
        url = 'budget:index'
        template = 'budget/index.html'

        login(client, django_user_model)

        # Check the page
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_one_year_summary(self, client, django_user_model):
        url = 'budget:one-year-summary'
        template = 'budget/one_year_summary.html'

        login(client, django_user_model)

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

    def test_bank_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.Bank',
            'budget:bank-detail', search_str=TEST_NAME,
            obj_params={'name': TEST_NAME})

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

    def test_bank_list_view(self, client, django_user_model):
        url = 'budget:bank-list'
        template = 'budget/bank-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_category_list_view(self, client, django_user_model):
        url = 'budget:category-list'
        template = 'budget/category-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_class_list_view(self, client, django_user_model):
        url = 'budget:class-list'
        template = 'budget/class-list.html'
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


class TestCreateViews:
    @staticmethod
    def create_view_test(client, model, url, template, user,
                         user_required=True, obj_params=None,
                         file_field=None):
        # Make sure there are no existing objects
        Model = apps.get_model(*model.split('.'))
        Model.objects.all().delete()
        assert Model.objects.count() == 0

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
                and Model.objects.count() == 1)
            if user_required:
                obj = Model.objects.first()
                assert obj.user == user
        except AssertionError:
            print(hr(response))
            raise

    def test_account_create_view(self, client, django_user_model):
        url = 'budget:account-add'
        model = 'budget.Account'
        template = 'budget/account-add.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['budget.Bank']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            name='TestObj', bank=parents['budget.Bank'].id)

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)

    def test_bank_create_view(self, client, django_user_model):
        url = 'budget:bank-add'
        model = 'budget.Bank'
        template = 'budget/bank-add.html'
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
        bank = acc.bank
        content = ','.join(
            [bank.date_col_name, bank.amt_col_name, bank.desc_col_name])
        csv = temp_file(content=content)

        obj_params = dict(
            upload_time=today_str(), account=acc.id, csv=csv)

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params, file_field='csv')


class TestUpdateViews:
    @staticmethod
    def update_view_test(client, model, url, template, user,
                         user_required=True, obj_params=None,
                         create_recursive=True):
        # Make sure there are no existing objects and make a new one
        Model = apps.get_model(*model.split('.'))
        Model.objects.all().delete()
        assert Model.objects.count() == 0
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
            obj = Model.objects.first()
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

        # Parents
        parent_models = ['budget.Bank']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            name='TestObj', bank=parents['budget.Bank'].id)

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)

    def test_bank_update_view(self, client, django_user_model):
        url = 'budget:bank-update'
        model = 'budget.Bank'
        template = 'budget/bank-update.html'
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
        Model = apps.get_model(*model.split('.'))
        Model.objects.all().delete()
        assert Model.objects.count() == 0

        # Create the object and assert success
        if obj_params is None:
            obj_params = dict()
        user = login(client, django_user_model)
        if user_required:
            obj_params.update(user=user)
        obj = mommy.make(model, **obj_params)
        obj = create_recursive_dependencies(obj)
        obj.save()
        assert Model.objects.count() == 1

        # Check the delete page
        response = client.get(reverse(url, kwargs={'pk': obj.id}))
        assert (
            response.status_code == 200
            and Model.objects.count() == 1)

        # Delete the object and verify
        response = client.post(reverse(url, kwargs={'pk': obj.id}))
        assert (
            response.status_code == 302
            and Model.objects.count() == 0)

    def test_account_delete_view(self, client, django_user_model):
        model = 'budget.Account'
        url = 'budget:account-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_bank_delete_view(self, client, django_user_model):
        model = 'budget.Bank'
        url = 'budget:bank-delete'
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
