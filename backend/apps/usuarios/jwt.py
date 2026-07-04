"""
Autenticación JWT amarrada al tenant (aislamiento multi-IPS a nivel de token).

Sin esto, un token emitido en la IPS A podría aceptarse en la IPS B si los
IDs de usuario coinciden entre esquemas. El claim "schema" se graba al emitir
(ver jwt_views.py) y aquí se exige que coincida con el tenant activo.

IMPORTANTE: este módulo lo importa la configuración de DRF al arrancar; no
importar aquí vistas/serializers de DRF (import circular). Las vistas viven
en jwt_views.py.
"""
from django.db import connection
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class TenantJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if token.get("schema") != connection.schema_name:
            raise InvalidToken("El token no fue emitido para esta IPS.")
        return token
