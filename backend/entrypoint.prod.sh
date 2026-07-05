#!/bin/sh
# Arranque de PRODUCCIÓN (Railway, servicio web): migra, publica estáticos,
# hace bootstrap idempotente (IPS principal + superusuario) y levanta Daphne
# en el puerto que asigna la plataforma.
set -e

export DJANGO_SETTINGS_MODULE=config.settings.prod

echo "==> Migraciones (todos los esquemas)..."
python manage.py migrate_schemas --noinput

echo "==> Estáticos del admin..."
python manage.py collectstatic --noinput

echo "==> Bootstrap de producción (idempotente)..."
python manage.py bootstrap_prod

echo "==> Daphne en 0.0.0.0:${PORT:-8000}..."
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
