"""Production settings.

Mandatory environment variables:
 - DJANGO_SETTINGS_MODULE=simplefi.settings.production
 - DJANGO_SECRET_KEY
 - DJANGO_HOST
 - EMAIL_HOST_USER
 - EMAIL_HOST_PASSWORD

Optional environment variables:
 - DATABASE_URL (defaults to sqlite3)
"""
# pylint: disable=wildcard-import,unused-wildcard-import
from .base import *

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = [os.environ["DJANGO_HOST"]]

# Email
EMAIL_USE_TLS = True
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_PORT = 587

# Registration
REGISTRATION_OPEN = True

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
