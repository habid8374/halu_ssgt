"""
Administración de personal de la IPS — rol coordinador.

Alta de médicos/especialistas, psicólogos SST, recepción, coordinadores y
usuarios del portal de empresas, con su ficha profesional y licencia SST.
Sin borrado físico: los usuarios se desactivan (`is_active`).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Usuario
from .permissions import EsCoordinador
from .roles import Rol
from .serializers import ROLES_GESTIONABLES, UsuarioSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    """Directorio de personal de la IPS. Solo el coordinador administra."""

    serializer_class = UsuarioSerializer
    permission_classes = [EsCoordinador]
    http_method_names = ["get", "post", "patch", "head", "options"]  # sin DELETE

    def get_queryset(self):
        qs = (
            Usuario.objects.select_related("sede", "empresa", "profesional")
            .exclude(rol=Rol.ADMIN_SISTEMA)  # el admin técnico no se lista aquí
            .order_by("nombre_completo")
        )
        rol = self.request.query_params.get("rol")
        if rol:
            qs = qs.filter(rol=rol)
        return qs

    @action(detail=False, methods=["get"])
    def roles(self, request):
        """Catálogo de roles que el coordinador puede dar de alta."""
        etiquetas = dict(Rol.choices)
        return Response(
            [{"valor": r, "etiqueta": etiquetas[r]} for r in
             [Rol.RECEPCION, Rol.MEDICO, Rol.PSICOLOGO_SST, Rol.COORDINADOR, Rol.EMPRESA_CLIENTE]
             if r in ROLES_GESTIONABLES]
        )
