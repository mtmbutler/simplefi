from django.contrib import admin

from .models import (
    Account,
    Budget,
    Category,
    Pattern,
    Transaction,
    TransactionClass,
    Upload,
)

admin.site.register(
    [Budget, Account, Upload, TransactionClass, Category, Pattern, Transaction]
)
