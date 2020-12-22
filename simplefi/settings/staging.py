"""Staging settings.

Mandatory environment variables:
 - DJANGO_SETTINGS_MODULE=simplefi.settings.staging
 - DJANGO_SECRET_KEY
 - DJANGO_HOST
 - EMAIL_HOST_USER
 - EMAIL_HOST_PASSWORD

Optional environment variables:
 - DATABASE_URL (defaults to sqlite3)
"""
# pylint: disable=wildcard-import,unused-wildcard-import
from .base import *

DEBUG = True
ALLOWED_HOSTS = [os.environ["DJANGO_HOST"]]

# Email
EMAIL_USE_TLS = True
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_PORT = 587

# Registration
REGISTRATION_OPEN = True
