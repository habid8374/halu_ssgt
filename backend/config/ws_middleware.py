"""
Middleware ASGI para WebSockets:

1. TenantWSMiddleware — resuelve el tenant (IPS) por hostname, igual que
   TenantMainMiddleware lo hace para HTTP, y lo deja en scope["tenant"].
2. JWTAuthWSMiddleware — autentica el WebSocket con el mismo token JWT de la
   API (query param ?token=), dentro del esquema del tenant. Si no hay token,
   el usuario queda anónimo (la pantalla pública de sala de espera lo permite;
   el tablero operativo NO — lo decide el consumer).
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _resolver_tenant(hostname: str):
    from django_tenants.utils import get_tenant_domain_model

    dominio = (
        get_tenant_domain_model()
        .objects.select_related("tenant")
        .filter(domain=hostname)
        .first()
    )
    return dominio.tenant if dominio else None


@database_sync_to_async
def _resolver_usuario(schema_name: str, token: str):
    from django.contrib.auth import get_user_model
    from django_tenants.utils import schema_context
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        access = AccessToken(token)
        with schema_context(schema_name):
            return get_user_model().objects.get(pk=access["user_id"])
    except Exception:
        return AnonymousUser()


class TenantWSMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode().split(":")[0]
        tenant = await _resolver_tenant(host)
        if tenant is None:
            # Sin tenant no hay tablero: cerrar el socket.
            await send({"type": "websocket.close", "code": 4404})
            return
        scope["tenant"] = tenant
        return await self.inner(scope, receive, send)


class JWTAuthWSMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        qs = parse_qs(scope.get("query_string", b"").decode())
        token = (qs.get("token") or [None])[0]
        if token and "tenant" in scope:
            scope["user"] = await _resolver_usuario(scope["tenant"].schema_name, token)
        else:
            scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)
