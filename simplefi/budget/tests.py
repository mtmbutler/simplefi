import datetime

from django.db import models
from django.urls import reverse
from model_mommy import mommy

from .models import Statement

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


class TestModels:
    def test_statement_date(self):
        s = Statement(account=None, year=2000, month=1, balance=0.00)
        assert s.date == datetime.date(year=2000, month=1, day=1)


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
    def test_bank_list_view(self, client, django_user_model):
        login(client, django_user_model)
        response = client.get(reverse('budget:bank-list'))
        assert response.status_code == 200


class TestCreateViews:
    pass
    # TODO: couldn't get the post to actually fill out the form
    # def test_bank_create_view(self, client, django_user_model):
    #     login(client, django_user_model)
    #     assert Bank.objects.count() == 0
    #
    #     post_data = dict(
    #         name='TestBank',
    #         date_col_name='date',
    #         amt_col_name='amount',
    #         desc_col_name='description')
    #     response = client.post(
    #         reverse('budget:bank-add'), post_data,
    #         content_type='application/json')
    #     print(str(response.content).replace('\\n', '\n'))
    #
    #     data = response.json()
    #     assert response.status_code == 201
    #     assert Bank.objects.count() == 1
    #     assert data == {
    #         'count': 1,
    #         'next': None,
    #         'previous': None,
    #         'results': [dict(
    #             pk=1,
    #             name='TestBank',
    #             date_col_name='date',
    #             amt_col_name='amount',
    #             desc_col_name='description',
    #             user_id=user.id)]}
