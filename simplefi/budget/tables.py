from typing import Any, Callable, Union, TYPE_CHECKING

import django_filters as filters
import django_tables2 as tables
from django.apps import apps
from django.urls import reverse

from budget import models

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.query import QuerySet
    from django.http import HttpRequest
    from django_tables2 import Column, Table


def user_filter(
    model: Union[str, 'Model']
) -> Callable[['HttpRequest'], 'QuerySet']:
    """Returns a function to filter a model on a request's user."""
    Model = apps.get_model(model)

    def f(request: 'HttpRequest') -> 'QuerySet':
        return Model.objects.filter(user=request.user)
    return f


def no_filter(
    model: Union[str, 'Model']
) -> Callable[[Any], 'QuerySet']:
    """Returns a function that gets all of a model's objects."""
    Model = apps.get_model(model)

    def f(__: Any) -> 'QuerySet':
        return Model.objects.all()
    return f


class SummingColumn(tables.Column):
    @staticmethod
    def render_footer(bound_column: 'Column', table: 'Table') -> float:
        return sum(bound_column.accessor.resolve(row) for row in table.data)


# -- ACCOUNTS --
class AccountTable(tables.Table):
    name = tables.Column(
        accessor='name',
        linkify=("budget:account-detail", {"pk": tables.A("pk")}))
    date_col_name = tables.Column(accessor='date_col_name')
    amt_col_name = tables.Column(accessor='amt_col_name')
    desc_col_name = tables.Column(accessor='desc_col_name')
    num_transactions = tables.Column(
        verbose_name='Transactions', accessor='num_transactions',
        orderable=False)

    class Meta:
        model = models.Account
        exclude = ('user', 'id')
        fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name', 'num_transactions']


# -- UPLOADS --
class UploadFilter(filters.FilterSet):
    account = filters.ModelChoiceFilter(
        queryset=user_filter('budget.Account'), label='Account')


class UploadTable(tables.Table):
    account = tables.Column(
        accessor='account',
        linkify=("budget:account-detail", {"pk": tables.A("account.pk")}))
    upload = tables.Column(
        accessor='__str__', order_by='upload_time',
        linkify=("budget:upload-detail", {"pk": tables.A("pk")}))
    num_transactions = tables.Column(
        verbose_name='Transactions', accessor='num_transactions',
        orderable=False)

    class Meta:
        model = models.Upload
        exclude = ('user', 'id')
        fields = ['account', 'upload', 'num_transactions']


# -- CLASSES --
class ClassTable(tables.Table):
    class_ = tables.Column(
        accessor='class_field',
        linkify=("budget:class-detail", {"pk": tables.A("class_field.pk")}))
    budget = tables.Column(
        verbose_name='Budget', accessor='fmt_value', order_by='value',
        linkify=("budget:budget-update", {"pk": tables.A("pk")}),
        attrs={'td': dict(align='right')})
    num_transactions = tables.Column(
        verbose_name='Transactions', accessor='num_class_transactions',
        orderable=False)

    class Meta:
        model = models.Budget
        exclude = ('user', 'id')
        fields = ['class_', 'budget', 'num_transactions']


# -- CATEGORIES --
class CategoryFilter(filters.FilterSet):
    class_field = filters.ModelChoiceFilter(
        queryset=no_filter('budget.TransactionClass'), label='Class')


class CategoryTable(tables.Table):
    class_ = tables.Column(
        accessor='class_field',
        linkify=("budget:class-detail", {"pk": tables.A("class_field.pk")}))
    name = tables.Column(
        verbose_name='Category', accessor='name',
        linkify=("budget:category-detail", {"pk": tables.A("pk")}))
    num_transactions = tables.Column(
        verbose_name='Transactions', accessor='num_transactions',
        orderable=False)

    class Meta:
        model = models.Category
        exclude = ('user', 'id')
        fields = ['class_', 'name', 'num_transactions']


# -- PATTERNS --
class PatternFilter(filters.FilterSet):
    category__class_field = filters.ModelChoiceFilter(
        queryset=no_filter('budget.TransactionClass'), label='Class')
    category = filters.ModelChoiceFilter(
        queryset=user_filter('budget.Category'), label='Category')


class PatternTable(tables.Table):
    class_ = tables.Column(
        accessor='class_field', orderable=False,
        linkify=("budget:class-detail", {"pk": tables.A("class_field.pk")}))
    category = tables.Column(
        accessor='category', orderable=False,
        linkify=("budget:category-detail", {"pk": tables.A("category.pk")}))
    pattern = tables.Column(
        verbose_name='Pattern', accessor='pattern',
        linkify=("budget:pattern-detail", {"pk": tables.A("pk")}))
    num_transactions = tables.Column(
        verbose_name='Transactions', accessor='num_transactions',
        orderable=False)

    class Meta:
        model = models.Pattern
        exclude = ('user', 'id')
        fields = ['class_', 'category', 'pattern', 'num_transactions']


# -- TRANSACTIONS --
class TransactionFilter(filters.FilterSet):
    upload = filters.ModelChoiceFilter(
        queryset=user_filter('budget.Upload'), label='Upload')
    upload__account = filters.ModelChoiceFilter(
        queryset=user_filter('budget.Account'), label='Account')
    pattern__category__class_field = filters.ModelChoiceFilter(
        queryset=no_filter('budget.TransactionClass'), label='Class')
    pattern__category = filters.ModelChoiceFilter(
        queryset=user_filter('budget.Category'), label='Category')
    date = filters.DateFromToRangeFilter(label='Date')
    amount = filters.RangeFilter()


class TransactionTable(tables.Table):
    account = tables.Column(
        accessor='account', orderable=False,
        linkify=("budget:account-detail", {"pk": tables.A("account.pk")}))
    class_ = tables.Column(
        accessor='class_field', orderable=False,
        linkify=("budget:class-detail", {"pk": tables.A("class_field.pk")}))
    category = tables.Column(
        accessor='category', orderable=False,
        linkify=("budget:category-detail", {"pk": tables.A("category.pk")}))
    upload = tables.Column(
        accessor='upload', orderable=False,
        linkify=("budget:upload-detail", {"pk": tables.A("upload.pk")}))
    date = tables.DateColumn(
        verbose_name='Date', accessor='date', format="d M Y")
    amount = tables.Column(
        'Amount', accessor='fmt_amt', order_by='amount',
        attrs={'td': dict(align='right')})
    description = tables.Column(
        accessor='trunc_desc', orderable=False,
        linkify=("budget:transaction-detail", {"pk": tables.A("pk")}))
    pattern = tables.Column(
        accessor='pattern', orderable=False, visible=False,
        linkify=("budget:pattern-detail", {"pk": tables.A("pattern.pk")}))

    class Meta:
        model = models.Transaction
        exclude = ('user', 'id')
        fields = [
            'upload', 'account', 'class_', 'category', 'date', 'amount',
            'description']


# -- SUMMARIES --
def linkify_class_by_name(name: str) -> str:
    model = apps.get_model('budget.TransactionClass')
    qs = model.objects.filter(name=name)
    if qs.count() != 1:
        print(qs.count())
        return reverse('budget:index')
    return qs.first().get_absolute_url()


def linkify_category_by_name(name: str) -> str:
    model = apps.get_model('budget.Category')
    qs = model.objects.filter(name__iexact=name)
    if qs.count() != 1:
        print(qs.count())
        return reverse('budget:index')
    return qs.first().get_absolute_url()


class SummaryTable(tables.Table):
    class_ = tables.Column(
        accessor='class_',
        linkify=lambda record: linkify_class_by_name(
            record["class_"].lower()))
    budget = tables.Column(
        accessor='budget', attrs={'td': dict(align='right')})


class ClassSummaryTable(tables.Table):
    category = tables.Column(
        accessor='category',
        linkify=lambda record: linkify_category_by_name(
            record["category"]))
