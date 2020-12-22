"""Development settings.

Mandatory environment variables:
 - DJANGO_SETTINGS_MODULE=simplefi.settings.development

Optional environment variables:
 - DATABASE_URL (defaults to sqlite3)
"""
# pylint: disable=wildcard-import,unused-wildcard-import
from .base import *

SECRET_KEY = "very_secret_key"  # nosec
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # nosec

# Email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Registration
REGISTRATION_OPEN = False
