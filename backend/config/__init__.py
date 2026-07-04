"""Expone la app de Celery al importar el paquete config."""
from .celery import app as celery_app

__all__ = ("celery_app",)
