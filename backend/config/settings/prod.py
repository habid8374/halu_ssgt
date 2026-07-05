"""
Producción (Railway + Vercel) — hardening OWASP Top 10.

La Res. 1888/2025 cita OWASP como marco exigido; este módulo aplica:
  A01 Control de acceso  -> permisos por objeto (ya en la API) + throttling.
  A02 Fallas cripto      -> TLS forzado, HSTS, cookies seguras, campos
                            clínicos cifrados con clave DEDICADA obligatoria.
  A03 Inyección          -> ORM (sin SQL crudo en el proyecto).
  A04 Diseño inseguro    -> multi-tenant por esquema + JWT amarrado a tenant.
  A05 Misconfiguración   -> DEBUG off, hosts explícitos, cabeceras seguras,
                            arranque falla si faltan secretos.
  A07 Fallas de authn    -> rate-limit del login, validadores de contraseña,
                            tokens cortos con rotación.
  A09 Logging            -> AuditLog append-only + logs sin datos clínicos.
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# --- Fail-fast: sin secretos reales no hay arranque (A05) -------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")  # sin default: obligatorio
CRYPTOGRAPHY_KEY = env("CRYPTOGRAPHY_KEY")  # clave DEDICADA para campos clínicos
if CRYPTOGRAPHY_KEY == SECRET_KEY:
    raise ImproperlyConfigured(
        "CRYPTOGRAPHY_KEY no puede ser igual a DJANGO_SECRET_KEY: usa una "
        "clave dedicada para el cifrado de campos clínicos (regla 10)."
    )

# --- Hosts / orígenes (explícitos, sin comodines) ---------------------------
# Incluir el dominio del backend (Railway) Y el del frontend (Vercel): el
# validador de Origin de los WebSockets compara contra ALLOWED_HOSTS.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOWED_ORIGIN_REGEXES = env.list("CORS_ALLOWED_ORIGIN_REGEXES", default=[])
CORS_ALLOW_ALL_ORIGINS = False

# --- Base de datos: DATABASE_URL de Railway + backend de django-tenants -----
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"
DATABASES["default"]["CONN_MAX_AGE"] = 60

# Redis de Railway (Channels + Celery ya leen REDIS_URL en base.py).

# --- TLS / cabeceras (A02, A05). Railway termina TLS en su proxy. ----------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 días; subir tras estabilizar
SECURE_HSTS_INCLUDE_SUBDOMAINS = False   # activar cuando haya dominio propio
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SAMESITE = "Lax"

# --- Estáticos del admin vía WhiteNoise (comprimidos, inmutables) -----------
STORAGES = globals().get("STORAGES", {})
STORAGES.setdefault("default", {"BACKEND": "django.core.files.storage.FileSystemStorage"})
STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}

# --- Logging: sin contenido clínico, solo metadatos (CLAUDE.md §7) ----------
LOGGING["root"]["level"] = "INFO"  # noqa: F405
