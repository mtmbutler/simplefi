"""Development settings.

Mandatory environment variables:
 - DJANGO_SETTINGS_MODULE=simplefi.settings.development
 - DJANGO_SECRET_KEY

Optional environment variables:
 - DATABASE_URL (defaults to sqlite3)
"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Registration
REGISTRATION_OPEN = False
