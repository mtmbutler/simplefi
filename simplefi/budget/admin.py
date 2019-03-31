from django.contrib import admin

from .models import (
    Bank, Budget, Account, Upload, TransactionClass, Category, Pattern,
    Transaction)

admin.site.register([
    Bank, Budget, Account, Upload, TransactionClass, Category, Pattern,
    Transaction])
