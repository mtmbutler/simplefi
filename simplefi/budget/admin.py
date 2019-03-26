from django.contrib import admin

from .models import Bank, Account, Upload, TransactionClass, Subcategory, Pattern, Transaction

admin.site.register([Bank, Account, Upload, TransactionClass, Subcategory, Pattern, Transaction])
