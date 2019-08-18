from django.contrib import admin

from .models import CreditLine, Statement

admin.site.register([CreditLine, Statement])
