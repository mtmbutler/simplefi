from django.contrib import admin

from .models import (
    Budget, Account, Upload, TransactionClass, Category, Pattern,
    Transaction)

admin.site.register([
    Budget, Account, Upload, TransactionClass, Category, Pattern,
    Transaction])
