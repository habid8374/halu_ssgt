"""Ajustes de desarrollo (Docker Compose)."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Dev multi-tenant: el frontend entra por localhost, demo2.localhost, etc.
CORS_ALLOW_ALL_ORIGINS = True

# Emails a consola en desarrollo.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery síncrono opcional para pruebas locales rápidas (desactivado por defecto).
CELERY_TASK_ALWAYS_EAGER = False
