import django_filters as filters
import django_tables2 as tables
from django.apps import apps

from budget import models


def user_filter(model):
    Model = apps.get_model(model)

    def f(request):
        return Model.objects.filter(user=request.user)
    return f


def no_filter(model):
    Model = apps.get_model(model)

    def f(__):
        return Model.objects.all()
    return f


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
