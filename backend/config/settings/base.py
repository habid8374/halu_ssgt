"""
Configuración base de Halu Salud Ocupacional.

Multi-tenant por esquema (un esquema por IPS) vía django-tenants.
Los ajustes sensibles se leen de variables de entorno (django-environ).
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "web"])

# --- Clave de cifrado para campos clínicos (CLAUDE.md regla 10) -------------
# NUNCA compartir esquema con SECRET_KEY en producción; rotación documentada
# en el manual de tratamiento de datos.
CRYPTOGRAPHY_KEY = env("CRYPTOGRAPHY_KEY", default=SECRET_KEY)

# --- django-tenants: separación de apps ------------------------------------
# SHARED_APPS viven en el esquema public; TENANT_APPS en el esquema de cada IPS.
# El esquema público también lleva auth/admin/usuarios para poder administrar
# las IPS y sus dominios desde el admin de Django (dominio dedicado, p. ej.
# admin.localhost en dev). Los datos clínicos/operativos reales SOLO viven en
# los esquemas de cada IPS.
SHARED_APPS = [
    "django_tenants",          # debe ir primero
    "apps.tenants",            # modelo IPS (tenant) + Dominio
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.usuarios",           # requerido por AUTH_USER_MODEL en public
    "apps.atenciones",         # dependencia de FK de usuarios (sede/empresa)
    "apps.historia_clinica",
    "apps.accidentes",
]

TENANT_APPS = [
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.messages",
    "django.contrib.sessions",
    "rest_framework",
    # apps de dominio (fase 1)
    "apps.usuarios",
    "apps.atenciones",
    "apps.historia_clinica",
    "apps.accidentes",         # scaffold; modelos en fase 2
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

TENANT_MODEL = "tenants.IPS"
TENANT_DOMAIN_MODEL = "tenants.Dominio"

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",  # primero: resuelve el esquema
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Base de datos: backend de django-tenants ------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env("POSTGRES_DB", default="halu_salud"),
        "USER": env("POSTGRES_USER", default="halu"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="halu"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
    }
}
DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

# --- Auth ------------------------------------------------------------------
AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- DRF -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # JWT con validación de tenant: el token queda amarrado al esquema
        # de la IPS que lo emitió (apps.usuarios.jwt).
        "apps.usuarios.jwt.TenantJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# --- Channels (tablero en tiempo real) -------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# --- Celery ----------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = "America/Bogota"
# Alertas de plazos normativos (FURAT/FUREL 2 días hábiles; adaptación 20
# días hábiles) — reglas 6 y 7 de CLAUDE.md.
CELERY_BEAT_SCHEDULE = {
    "revisar-plazos-cumplimiento": {
        "task": "apps.accidentes.tasks.revisar_plazos",
        "schedule": 60 * 60,  # cada hora
    },
}

# --- Almacenamiento de objetos (DocumentoAdjunto) --------------------------
# Abstraído: FileSystemStorage en dev; S3-compatible (MinIO/S3) por env.
STORAGE_BACKEND = env("STORAGE_BACKEND", default="filesystem")
if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="halu-adjuntos")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_FILE_OVERWRITE = False
    # Cifrado en reposo del bucket configurado a nivel de proveedor.

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- CORS -------------------------------------------------------------------
# Multi-tenant: cada IPS entra por su propio dominio, así que el frontend
# puede originarse en N hosts. En producción se permite por regex (p. ej.
# ^https://[a-z0-9-]+\.halu\.co$). En dev, dev.py abre todos los orígenes.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOWED_ORIGIN_REGEXES = env.list("CORS_ALLOWED_ORIGIN_REGEXES", default=[])

# --- Internacionalización --------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Logging: NUNCA loggear contenido de historia clínica (CLAUDE.md §7) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
