"""Routing WebSocket del tablero de flujo en tiempo real."""
from django.urls import re_path

from apps.atenciones.consumers import TableroConsumer

websocket_urlpatterns = [
    re_path(r"^ws/tablero/(?P<sede_id>\d+)/$", TableroConsumer.as_asgi()),
]
