"""
API de la batería de riesgo psicosocial (Res. 2404/2019 — regla 4).

- Instrumentos individuales: SOLO el psicólogo que los aplicó (queryset
  scoping + has_object_permission). Ningún otro rol, jamás.
- Consolidado: agregados anónimos por empresa/nivel para coordinador y
  empresa_cliente (su propia empresa), con mínimo de registros para
  proteger el anonimato.
"""
from django.db.models import Count
from rest_framework import serializers, viewsets
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.roles import Rol

from .models import InstrumentoPsicosocial

MINIMO_ANONIMATO = 3  # no se reportan grupos con menos registros


class EsPsicologo(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.rol == Rol.PSICOLOGO_SST
        )

    def has_object_permission(self, request, view, obj):
        return obj.aplicado_por_id == request.user.id


class InstrumentoSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = InstrumentoPsicosocial
        fields = [
            "id", "trabajador", "trabajador_nombre", "atencion", "tipo",
            "fecha_aplicacion", "nivel_riesgo", "contenido", "created_at",
        ]

    def get_trabajador_nombre(self, obj):
        return f"{obj.trabajador.nombres} {obj.trabajador.apellidos}"

    def create(self, validated_data):
        validated_data["aplicado_por"] = self.context["request"].user
        return super().create(validated_data)


class InstrumentoViewSet(viewsets.ModelViewSet):
    queryset = InstrumentoPsicosocial.objects.filter(archivado=False).select_related("trabajador")
    serializer_class = InstrumentoSerializer
    permission_classes = [EsPsicologo]
    http_method_names = ["get", "post", "patch", "head", "options"]  # sin DELETE (retención)

    def get_queryset(self):
        # Custodia: solo instrumentos aplicados por ESTE psicólogo.
        return super().get_queryset().filter(aplicado_por=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        from apps.usuarios.audit import ip_de, registrar
        from apps.usuarios.models import AccionAudit

        instance = self.get_object()
        registrar(request.user, AccionAudit.VER, instance, ip=ip_de(request))
        return super().retrieve(request, *args, **kwargs)


class ConsolidadoView(APIView):
    """
    Informe consolidado agregado: conteos por tipo de instrumento y nivel de
    riesgo. empresa_cliente solo su empresa; coordinador y psicólogo pueden
    filtrar con ?empresa=. Nunca expone instrumentos individuales.
    """

    def get(self, request):
        user = request.user
        if user.rol == Rol.EMPRESA_CLIENTE:
            empresa_id = user.empresa_id
        elif user.rol in {Rol.COORDINADOR, Rol.PSICOLOGO_SST}:
            empresa_id = request.query_params.get("empresa")
        else:
            return Response(status=403)

        qs = InstrumentoPsicosocial.objects.filter(archivado=False)
        if empresa_id:
            qs = qs.filter(trabajador__empresa_id=empresa_id)

        total = qs.count()
        if total < MINIMO_ANONIMATO:
            return Response({
                "total": total,
                "detalle": [],
                "nota": f"Se requieren al menos {MINIMO_ANONIMATO} instrumentos para el informe agregado.",
            })

        detalle = list(
            qs.values("tipo", "nivel_riesgo").annotate(cantidad=Count("id")).order_by("tipo", "nivel_riesgo")
        )
        return Response({"total": total, "detalle": detalle})
