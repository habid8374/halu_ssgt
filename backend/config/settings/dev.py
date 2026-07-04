"""Ajustes de desarrollo (Docker Compose)."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Emails a consola en desarrollo.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery síncrono opcional para pruebas locales rápidas (desactivado por defecto).
CELERY_TASK_ALWAYS_EAGER = False
