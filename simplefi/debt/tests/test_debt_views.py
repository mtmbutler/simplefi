import datetime
import os
import random
import string

from django.apps import apps
from django.db import models
from django.urls import reverse
from django.utils import timezone
from model_mommy import mommy

from debt.tests.utils import login

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
        url = 'debt:index'
        template = 'debt/index.html'

        login(client, django_user_model)

        # Check the page
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_debt_summary(self, client, django_user_model):
        url = 'debt:debt-summary'
        template = 'debt/debt_summary.html'

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

    def test_accountholder_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'debt.AccountHolder',
            'debt:accountholder-detail', search_str=TEST_NAME,
            obj_params={'name': TEST_NAME})

    def test_account_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'debt.CreditLine',
            'debt:account-detail', search_str=TEST_NAME,
            obj_params={'name': TEST_NAME})


class TestListViews:
    @staticmethod
    def list_view_test(client, django_user_model, url, template):
        login(client, django_user_model)
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

    def test_account_list_view(self, client, django_user_model):
        url = 'debt:account-list'
        template = 'debt/account-list.html'
        self.list_view_test(client, django_user_model, url, template)

    def test_accountholder_list_view(self, client, django_user_model):
        url = 'debt:accountholder-list'
        template = 'debt/accountholder-list.html'
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
        url = 'debt:account-add'
        model = 'debt.CreditLine'
        template = 'debt/account-add.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['debt.AccountHolder']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            name='TestObj',
            holder=parents['debt.AccountHolder'].id,
            statement_date=1, date_opened=today_str(), annual_fee=0,
            interest_rate=0, credit_line=0, min_pay_pct=0, min_pay_dlr=0,
            priority=0)

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)

    def test_accountholder_create_view(self, client, django_user_model):
        url = 'debt:accountholder-add'
        model = 'debt.AccountHolder'
        template = 'debt/accountholder-add.html'
        user = login(client, django_user_model)
        obj_params = dict(name='TestObj')

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)

    def test_statement_create_view(self, client, django_user_model):
        url = 'debt:statement-add'
        model = 'debt.Statement'
        template = 'debt/statement-add.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['debt.CreditLine']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            account=parents['debt.CreditLine'].id,
            year=2000, month=1, balance=0)

        self.create_view_test(
            client, model, url, template, user,
            obj_params=obj_params)


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
        url = 'debt:account-update'
        model = 'debt.CreditLine'
        template = 'debt/account-update.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['debt.AccountHolder']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            name='TestObj',
            holder=parents['debt.AccountHolder'].id,
            statement_date=1, date_opened=today_str(), annual_fee=0,
            interest_rate=0, credit_line=0, min_pay_pct=0, min_pay_dlr=0,
            priority=0)

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)

    def test_accountholder_update_view(self, client, django_user_model):
        url = 'debt:accountholder-update'
        model = 'debt.AccountHolder'
        template = 'debt/accountholder-update.html'
        user = login(client, django_user_model)
        obj_params = dict(name='TestObj')

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)

    def test_statement_update_view(self, client, django_user_model):
        url = 'debt:statement-update'
        model = 'debt.Statement'
        template = 'debt/statement-update.html'
        user = login(client, django_user_model)

        # Parents
        parent_models = ['debt.CreditLine']
        parents = parent_obj_set(parent_models)

        obj_params = dict(
            account=parents['debt.CreditLine'].id,
            year=2000, month=1, balance=0)

        self.update_view_test(
            client, model, url, template, user,
            user_required=True, obj_params=obj_params)


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
        print(obj.pk)
        assert Model.objects.count() == 1

        # Check the delete page
        response = client.get(reverse(url, kwargs={'pk': obj.pk}))
        assert (
            response.status_code == 200
            and Model.objects.count() == 1)

        # Delete the object and verify
        response = client.post(reverse(url, kwargs={'pk': obj.pk}))
        assert (
            response.status_code == 302
            and Model.objects.count() == 0)

    def test_account_delete_view(self, client, django_user_model):
        model = 'debt.CreditLine'
        url = 'debt:account-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_accountholder_delete_view(self, client, django_user_model):
        model = 'debt.AccountHolder'
        url = 'debt:accountholder-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_statement_delete_view(self, client, django_user_model):
        model = 'debt.Statement'
        url = 'debt:statement-delete'
        self.delete_view_test(client, django_user_model, model, url)
