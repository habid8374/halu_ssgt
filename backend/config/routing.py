"""
Routing WebSocket del tablero de flujo.

El consumer real (TableroConsumer) se implementa en el paso 5 del plan de
fase 1, una vez aprobado el diseño de modelos. Se deja la lista vacía para
mantener el ASGI arrancable mientras tanto.
"""
from django.urls import re_path  # noqa: F401

websocket_urlpatterns = [
    # re_path(r"ws/tablero/(?P<sede_id>\d+)/$", TableroConsumer.as_asgi()),
]
