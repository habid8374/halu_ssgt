#!/bin/sh
# Arranque de desarrollo: migra todos los esquemas, siembra datos demo
# (idempotente) y levanta Daphne (HTTP + WebSocket).
set -e

echo "==> Aplicando migraciones (shared + tenants)..."
python manage.py migrate_schemas --noinput

echo "==> Sembrando datos de demostración (idempotente)..."
python manage.py seed_demo

echo "==> Iniciando Daphne en 0.0.0.0:8000..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
