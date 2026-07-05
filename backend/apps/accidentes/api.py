"""
API de accidentes/enfermedad laboral y alertas de cumplimiento.

Roles: coordinador gestiona todo; recepción puede registrar el evento.
empresa_cliente NO accede (el reporte a la ARL es responsabilidad de la IPS
en este flujo; el portal de empresa no expone datos del módulo).
"""
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.usuarios.roles import Rol

from .models import (
    AccidenteTrabajo,
    Alerta,
    InvestigacionAccidente,
    ReporteFUREL,
    ReporteFURAT,
    TipoEvento,
)
from .utils import sumar_dias_habiles


class EsCoordinadorORecepcion(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.rol == Rol.COORDINADOR:
            return True
        # Recepción solo registra/lee; no marca envíos ni resuelve alertas.
        return u.rol == Rol.RECEPCION and view.action in {"list", "retrieve", "create"}


class EsCoordinador(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.rol == Rol.COORDINADOR
        )


class ReporteSerializer(serializers.Serializer):
    estado = serializers.CharField(read_only=True)
    fecha_limite = serializers.DateField(read_only=True)
    enviado_at = serializers.DateTimeField(read_only=True)
    radicado_arl = serializers.CharField(read_only=True)


class AccidenteSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.SerializerMethodField()
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    reporte = serializers.SerializerMethodField()

    class Meta:
        model = AccidenteTrabajo
        fields = [
            "id", "tipo_evento", "trabajador", "trabajador_nombre", "empresa",
            "empresa_nombre", "sede", "fecha_evento", "gravedad", "descripcion",
            "arl_nombre", "reporte", "created_at",
        ]
        read_only_fields = ["empresa"]

    def get_trabajador_nombre(self, obj):
        return f"{obj.trabajador.nombres} {obj.trabajador.apellidos}"

    def get_reporte(self, obj):
        rep = getattr(obj, "furat", None) if obj.tipo_evento == TipoEvento.ACCIDENTE else getattr(obj, "furel", None)
        return ReporteSerializer(rep).data if rep else None

    def validate(self, data):
        if "trabajador" in data:
            data["empresa"] = data["trabajador"].empresa
        return data

    def create(self, validated_data):
        validated_data["registrado_por"] = self.context["request"].user
        accidente = super().create(validated_data)
        # Reporte ARL con plazo de 2 días hábiles (regla 6) e investigación
        # (Res. 1401/2007: 15 días; se usa calendario para el límite).
        if accidente.tipo_evento == TipoEvento.ACCIDENTE:
            ReporteFURAT.objects.create(accidente=accidente)
        else:
            ReporteFUREL.objects.create(accidente=accidente)
        InvestigacionAccidente.objects.create(
            accidente=accidente,
            fecha_limite=sumar_dias_habiles(accidente.fecha_evento, 11),  # ~15 días calendario
        )
        return accidente


class AccidenteViewSet(viewsets.ModelViewSet):
    queryset = AccidenteTrabajo.objects.select_related("trabajador", "empresa").all()
    serializer_class = AccidenteSerializer
    permission_classes = [EsCoordinadorORecepcion]
    http_method_names = ["get", "post", "patch", "head", "options"]

    @action(detail=True, methods=["post"], permission_classes=[EsCoordinador])
    def marcar_enviado(self, request, pk=None):
        """Registra el envío del FURAT/FUREL a la ARL (con radicado)."""
        accidente = self.get_object()
        rep = (
            getattr(accidente, "furat", None)
            if accidente.tipo_evento == TipoEvento.ACCIDENTE
            else getattr(accidente, "furel", None)
        )
        if rep is None:
            return Response({"detail": "El evento no tiene reporte."}, status=status.HTTP_409_CONFLICT)
        if rep.estado == "enviado":
            return Response({"detail": "El reporte ya fue enviado."}, status=status.HTTP_409_CONFLICT)
        rep.marcar_enviado(radicado=request.data.get("radicado", ""))
        return Response(AccidenteSerializer(accidente).data)


class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = ["id", "tipo", "mensaje", "vence", "vencida", "resuelta", "created_at"]


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    """Bandeja de alertas de plazo — solo coordinación (matriz §4)."""

    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    permission_classes = [EsCoordinador]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("abiertas") == "1":
            qs = qs.filter(resuelta=False)
        return qs

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        alerta.resuelta = True
        alerta.save(update_fields=["resuelta"])
        return Response(AlertaSerializer(alerta).data)
