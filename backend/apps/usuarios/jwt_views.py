"""
Emisión de tokens con claim de tenant. Ver jwt.py para la validación.
Separado de jwt.py para evitar el import circular con la configuración DRF.
"""
from django.db import connection
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Amarra el token al esquema de la IPS que autenticó al usuario.
        # simplejwt propaga los claims del refresh al access automáticamente.
        token["schema"] = connection.schema_name
        return token


class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer
    # OWASP A07: rate-limit dedicado del login (DEFAULT_THROTTLE_RATES["token"]).
    throttle_scope = "token"
