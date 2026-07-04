from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.permissions import (
    EsRecepcion,
    PuedeTransicionarAtencion,
    PuedeVerTablero,
    scope_atenciones,
)
from apps.usuarios.roles import Rol

from .models import Atencion, Consultorio, Sede, Trabajador, TransicionInvalidaError
from .serializers import (
    AtencionSerializer,
    ConsultorioSerializer,
    CrearAtencionSerializer,
    HistorialEstadoSerializer,
    SedeSerializer,
    TrabajadorSerializer,
    TransicionSerializer,
)
from .services import transicionar_atencion


class SedeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sede.objects.filter(activa=True)
    serializer_class = SedeSerializer
    permission_classes = [PuedeVerTablero]


class ConsultorioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Consultorio.objects.filter(activo=True)
    serializer_class = ConsultorioSerializer
    permission_classes = [PuedeVerTablero]

    def get_queryset(self):
        qs = super().get_queryset()
        sede_id = self.request.query_params.get("sede")
        return qs.filter(sede_id=sede_id) if sede_id else qs


class TrabajadorViewSet(viewsets.ModelViewSet):
    """Registro de trabajadores en admisión. Solo recepción escribe."""

    queryset = Trabajador.objects.filter(archivado=False).select_related("empresa")
    serializer_class = TrabajadorSerializer
    permission_classes = [EsRecepcion]

    def get_queryset(self):
        qs = super().get_queryset()
        doc = self.request.query_params.get("documento")
        return qs.filter(numero_documento=doc) if doc else qs

    def destroy(self, request, *args, **kwargs):
        # Retención 15 años (regla 2): nunca borrado físico, solo archivado.
        trabajador = self.get_object()
        trabajador.archivado = True
        trabajador.save(update_fields=["archivado"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AtencionViewSet(viewsets.ModelViewSet):
    """
    Atenciones del tablero. Scoping por rol en get_queryset (capa 1) +
    has_object_permission (capa 2). La transición de estado SOLO vía
    /transicion/ — el campo estado es read-only en el serializer.
    """

    queryset = (
        Atencion.objects.select_related(
            "trabajador", "empresa", "sede", "consultorio", "profesional_asignado"
        )
    )
    http_method_names = ["get", "post", "patch", "head", "options"]  # sin DELETE

    def get_permissions(self):
        if self.action == "create":
            return [EsRecepcion()]
        if self.action == "transicion":
            return [PuedeTransicionarAtencion()]
        return [PuedeVerTablero()]

    def get_serializer_class(self):
        return CrearAtencionSerializer if self.action == "create" else AtencionSerializer

    def get_queryset(self):
        qs = scope_atenciones(self.request.user, super().get_queryset())
        sede_id = self.request.query_params.get("sede")
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        if self.request.query_params.get("activas") == "1":
            qs = qs.exclude(estado="finalizado")
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        atencion = serializer.save()
        return Response(
            AtencionSerializer(atencion).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def transicion(self, request, pk=None):
        """Cambia el estado (máquina de estados) y emite el evento al tablero."""
        atencion = self.get_object()
        serializer = TransicionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            transicionar_atencion(
                atencion,
                serializer.validated_data["estado"],
                request.user,
                serializer.validated_data.get("nota", ""),
            )
        except TransicionInvalidaError as e:
            return Response({"detail": e.messages[0]}, status=status.HTTP_409_CONFLICT)
        return Response(AtencionSerializer(atencion).data)

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        atencion = self.get_object()
        data = HistorialEstadoSerializer(
            atencion.historial_estados.select_related("usuario"), many=True
        ).data
        return Response(data)


class MeView(viewsets.ViewSet):
    """Identidad del usuario autenticado (rol y scope) para el frontend."""

    def list(self, request):
        u = request.user
        return Response(
            {
                "id": u.id,
                "email": u.email,
                "nombre_completo": u.nombre_completo,
                "rol": u.rol,
                "sede": u.sede_id,
                "empresa": u.empresa_id,
                "es_coordinador": u.rol == Rol.COORDINADOR,
            }
        )
