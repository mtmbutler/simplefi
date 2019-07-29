import datetime
from typing import TYPE_CHECKING

from django.urls import reverse
from model_mommy import mommy

from budget import forms, tables, utils
from budget.tests.utils import login

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client


def test_safe_strftime_valid():
    dt = datetime.datetime(2018, 11, 10, 15, 30, 0)
    assert utils.safe_strftime(dt, '%y%m%d %H%M%S') == '181110 153000'


def test_safe_strftime_invalid():
    assert utils.safe_strftime('non-dt str', '%Y%M%D %h%m%s') == 'non-dt str'


class TestCategoryClassChoiceField:
    def test_label_from_instance(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        login(client, django_user_model)
        tclass = mommy.make('budget.TransactionClass', name='foo')
        cat = mommy.make('budget.Category', class_field=tclass, name='bar')
        label = forms.CategoryClassChoiceField.label_from_instance(None, cat)
        assert label == 'foo - bar'


class TestTableLinkifies:
    def test_linkify_class_valid(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        login(client, django_user_model)
        tclass = mommy.make('budget.TransactionClass', name='foo')
        url = tables.linkify_class_by_name('foo')

        # Should link to a detail view for the existing class
        assert url == reverse('budget:class-detail', kwargs={'pk': tclass.pk})

    def test_linkify_class_invalid(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        login(client, django_user_model)
        url = tables.linkify_class_by_name('foo')

        # Should link to the list view; since there is no 'foo' in the DB
        assert url == reverse('budget:index')

    def test_linkify_category_valid(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        login(client, django_user_model)
        cat = mommy.make('budget.Category', name='foo')
        url = tables.linkify_category_by_name('foo')

        # Should link to a detail view for the existing class
        assert url == reverse('budget:category-detail', kwargs={'pk': cat.pk})

    def test_linkify_category_invalid(
        self,
        client: 'Client',
        django_user_model: 'User'
    ):
        login(client, django_user_model)
        url = tables.linkify_category_by_name('foo')

        # Should link to the list view; since there is no 'foo' in the DB
        assert url == reverse('budget:index')
