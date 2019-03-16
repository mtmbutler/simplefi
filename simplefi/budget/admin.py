from django.contrib import admin

from .models import Bank, Account, Upload, Category, Subcategory, Pattern, Transaction

admin.site.register([Bank, Account, Upload, Category, Subcategory, Pattern, Transaction])
