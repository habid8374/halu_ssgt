"""
Aislamiento del backend de cifrado a nivel de columna (CLAUDE.md regla 10).

Todos los campos clínicos sensibles se declaran con EncryptedTextField /
EncryptedCharField. Si algún día se cambia de django-cryptography a pgcrypto
u otro proveedor, solo se toca este módulo — los modelos no cambian.

Decisión confirmada: cifrado app-level (Fernet) con clave gestionada por la
app (settings.CRYPTOGRAPHY_KEY), fuera de la base de datos.
"""
from django_cryptography.fields import encrypt
from django.db import models


def EncryptedTextField(**kwargs):
    return encrypt(models.TextField(**kwargs))


def EncryptedCharField(**kwargs):
    return encrypt(models.CharField(**kwargs))
