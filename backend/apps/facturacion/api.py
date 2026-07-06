"""
API de facturación. Coordinador gestiona; empresa_cliente SOLO lee sus
facturas emitidas (motor estándar). El motor ARL es exclusivo del coordinador.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.atenciones.models import Atencion
from apps.usuarios.roles import Rol

from .models import Factura, FacturaARL, FacturaItem, TarifaConvenio
from .rips import construir_rips, validar_en_muv


class PermisoFacturacion(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.rol == Rol.COORDINADOR:
            return True
        return u.rol == Rol.EMPRESA_CLIENTE and request.method in SAFE_METHODS


class EsCoordinador(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.rol == Rol.COORDINADOR
        )


class TarifaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = TarifaConvenio
        fields = ["id", "empresa", "empresa_nombre", "tipo_examen", "valor"]


class TarifaViewSet(viewsets.ModelViewSet):
    queryset = TarifaConvenio.objects.select_related("empresa")
    serializer_class = TarifaSerializer
    permission_classes = [EsCoordinador]


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacturaItem
        fields = ["id", "atencion", "descripcion", "valor"]


class FacturaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    items = ItemSerializer(many=True, read_only=True)

    class Meta:
        model = Factura
        fields = [
            "id", "numero", "empresa", "empresa_nombre", "periodo_desde",
            "periodo_hasta", "estado", "total", "items", "emitida_at", "created_at",
        ]


class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
    """Motor estándar. La creación va por /facturas/generar/ (borrador)."""

    queryset = Factura.objects.select_related("empresa").prefetch_related("items")
    serializer_class = FacturaSerializer
    permission_classes = [PermisoFacturacion]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.rol == Rol.EMPRESA_CLIENTE:
            # La empresa solo ve SUS facturas ya emitidas.
            return qs.filter(empresa=u.empresa).exclude(estado="borrador")
        return qs

    @action(detail=False, methods=["post"], permission_classes=[EsCoordinador])
    def generar(self, request):
        """
        Crea un borrador con las atenciones FINALIZADAS de la empresa en el
        período que aún no han sido facturadas, valoradas según tarifario.
        """
        empresa_id = request.data.get("empresa")
        desde, hasta = request.data.get("desde"), request.data.get("hasta")
        if not (empresa_id and desde and hasta):
            return Response({"detail": "empresa, desde y hasta son obligatorios."}, status=400)

        atenciones = Atencion.objects.filter(
            empresa_id=empresa_id, estado="finalizado",
            created_at__date__gte=desde, created_at__date__lte=hasta,
            factura_item__isnull=True,
        ).select_related("trabajador")
        if not atenciones.exists():
            return Response({"detail": "No hay atenciones finalizadas sin facturar en el período."}, status=409)

        tarifas = {
            t.tipo_examen: t.valor
            for t in TarifaConvenio.objects.filter(empresa_id=empresa_id)
        }
        factura = Factura.objects.create(
            empresa_id=empresa_id, periodo_desde=desde, periodo_hasta=hasta,
            creada_por=request.user,
        )
        total = Decimal("0")
        for a in atenciones:
            valor = tarifas.get(a.tipo_examen, Decimal("0"))
            FacturaItem.objects.create(
                factura=factura, atencion=a,
                descripcion=f"{a.get_tipo_examen_display()} — {a.trabajador.nombre_completo}",
                valor=valor,
            )
            total += valor
        factura.total = total
        factura.save(update_fields=["total"])
        return Response(FacturaSerializer(factura).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[EsCoordinador])
    def emitir(self, request, pk=None):
        factura = self.get_object()
        try:
            factura.emitir()
        except Exception as e:
            return Response({"detail": str(e)}, status=409)
        return Response(FacturaSerializer(factura).data)

    @action(detail=True, methods=["post"], permission_classes=[EsCoordinador])
    def marcar_pagada(self, request, pk=None):
        factura = self.get_object()
        if factura.estado != "emitida":
            return Response({"detail": "Solo se marca pagada una factura emitida."}, status=409)
        factura.estado = "pagada"
        factura.save(update_fields=["estado"])
        return Response(FacturaSerializer(factura).data)


class FacturaARLSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = FacturaARL
        fields = [
            "id", "numero", "accidente", "atencion", "trabajador_nombre",
            "valor", "estado", "cuv", "cucon", "rips_json", "created_at",
        ]
        read_only_fields = ["estado", "cuv", "rips_json", "numero"]

    def get_trabajador_nombre(self, obj):
        t = obj.accidente.trabajador
        return t.nombre_completo

    def create(self, validated_data):
        validated_data["creada_por"] = self.context["request"].user
        factura = FacturaARL(**validated_data)
        # Regla 8: la atención debe corresponder al accidente (clean()).
        factura.full_clean(exclude=["rips_json", "numero", "cuv", "cucon"])
        factura.save()
        factura.numero = f"FA-{factura.pk:06d}"
        factura.rips_json = construir_rips(factura)
        factura.save(update_fields=["numero", "rips_json"])
        return factura


class FacturaARLViewSet(viewsets.ModelViewSet):
    """
    Motor RIPS/ARL: SOLO coordinador, SOLO sobre accidentes registrados.
    Los exámenes ocupacionales ordinarios jamás pasan por aquí (regla 8).
    """

    queryset = FacturaARL.objects.select_related("accidente", "accidente__trabajador")
    serializer_class = FacturaARLSerializer
    permission_classes = [EsCoordinador]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def validar_muv(self, request, pk=None):
        """Obtiene el CUV del MUV (adaptador stub en desarrollo)."""
        factura = self.get_object()
        if factura.estado != "borrador":
            return Response({"detail": f"Ya está {factura.estado}."}, status=409)
        factura.cuv = validar_en_muv(factura)
        factura.estado = "validada"
        factura.save(update_fields=["cuv", "estado"])
        return Response(FacturaARLSerializer(factura).data)
