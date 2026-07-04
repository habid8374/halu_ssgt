"""
ASGI: HTTP (Django) + WebSocket (Channels) para el tablero en tiempo real.

Cadena WS: AllowedHosts → resolución de tenant (IPS) → autenticación JWT →
TableroConsumer.
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

# Importar después de inicializar Django.
from config.routing import websocket_urlpatterns  # noqa: E402
from config.ws_middleware import JWTAuthWSMiddleware, TenantWSMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            TenantWSMiddleware(
                JWTAuthWSMiddleware(URLRouter(websocket_urlpatterns))
            )
        ),
    }
)
