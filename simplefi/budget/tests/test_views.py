from django.apps import apps
from django.db import models
from django.urls import reverse
from model_mommy import mommy

TEST_NAME = 'Scooby Doo'


def login(client, django_user_model):
    params = dict(
        username="test",
        password="testpw")
    user = django_user_model.objects.create_user(**params)
    client.login(**params)

    return user


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

    def test_accountholder_detail_view(self, client, django_user_model):
        self.detail_view_test(
            client, django_user_model, 'budget.AccountHolder',
            'budget:accountholder-detail', search_str=TEST_NAME,
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

    def test_accountholder_list_view(self, client, django_user_model):
        url = 'budget:accountholder-list'
        template = 'budget/accountholder-list.html'
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
    def create_view_test(client, django_user_model, model, url,
                         template, user_required=True, obj_params=None):
        # Make sure there are no existing objects
        Model = apps.get_model(*model.split('.'))
        Model.objects.all().delete()
        assert Model.objects.count() == 0

        # Check the create page
        user = login(client, django_user_model)
        response = client.get(reverse(url))
        tp_names = [t.name for t in response.templates]
        assert response.status_code == 200 and template in tp_names

        # Use the create page to create obj and assert success
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

    def test_accountholder_create_view(self, client, django_user_model):
        url = 'budget:accountholder-add'
        model = 'budget.AccountHolder'
        template = 'budget/accountholder-add.html'
        obj_params = dict(name='TestObj')

        self.create_view_test(
            client, django_user_model, model, url, template,
            obj_params=obj_params)

    def test_category_create_view(self, client, django_user_model):
        url = 'budget:category-add'
        model = 'budget.Category'
        template = 'budget/category-add.html'

        # Parents
        klass = mommy.make('budget.TransactionClass')
        klass = create_recursive_dependencies(klass)
        klass.save()

        obj_params = dict(name='TestObj', class_field=klass.id)

        self.create_view_test(
            client, django_user_model, model, url, template,
            obj_params=obj_params)


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

    def test_accountholder_delete_view(self, client, django_user_model):
        model = 'budget.AccountHolder'
        url = 'budget:accountholder-delete'
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

    def test_statement_delete_view(self, client, django_user_model):
        model = 'budget.Statement'
        url = 'budget:statement-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_transaction_delete_view(self, client, django_user_model):
        model = 'budget.Transaction'
        url = 'budget:transaction-delete'
        self.delete_view_test(client, django_user_model, model, url)

    def test_upload_delete_view(self, client, django_user_model):
        model = 'budget.Upload'
        url = 'budget:upload-delete'
        self.delete_view_test(client, django_user_model, model, url)
