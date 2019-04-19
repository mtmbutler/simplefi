import django_tables2 as tables
from django_filters import FilterSet

from budget import models


class TransactionFilter(FilterSet):
    class Meta:
        model = models.Transaction
        fields = [
            'upload__account', 'date', 'amount', 'description', 'pattern',
            'pattern__category']


class TransactionTable(tables.Table):
    class Meta:
        model = models.Transaction
        account = tables.Column(accessor='upload__account')
        category = tables.Column(accessor='pattern__category')

        fields = [
            'account', 'date', 'amount', 'description', 'pattern', 'category']
