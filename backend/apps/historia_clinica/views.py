from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.audit import ip_de, registrar
from apps.usuarios.models import AccionAudit
from apps.usuarios.permissions import (
    EsMedicoTratante,
    PuedeVerConcepto,
    PuedeVerHistoriaClinica,
    scope_conceptos,
    scope_historias,
)
from apps.usuarios.roles import Rol

from .models import (
    ConceptoMedicoOcupacional,
    Diagnostico,
    HistoriaClinicaOcupacional,
    OrdenMedica,
    Receta,
)
from .serializers import (
    ConceptoSerializer,
    DiagnosticoSerializer,
    FirmarConceptoSerializer,
    HistoriaClinicaSerializer,
    OrdenMedicaSerializer,
    RecetaSerializer,
)


class HistoriaClinicaViewSet(viewsets.ModelViewSet):
    """
    Historia clínica ocupacional. Regla 1: SOLO médico asignado. Regla 9:
    toda lectura y escritura queda en AuditLog. Sin DELETE (regla 2:
    retención 15 años — se archiva, nunca se borra).
    """

    queryset = HistoriaClinicaOcupacional.objects.filter(archivada=False).select_related(
        "atencion", "atencion__trabajador"
    )
    serializer_class = HistoriaClinicaSerializer
    permission_classes = [PuedeVerHistoriaClinica]
    http_method_names = ["get", "post", "patch", "head", "options"]  # sin DELETE

    def get_queryset(self):
        qs = scope_historias(self.request.user, super().get_queryset())
        atencion_id = self.request.query_params.get("atencion")
        return qs.filter(atencion_id=atencion_id) if atencion_id else qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        registrar(request.user, AccionAudit.VER, instance, ip=ip_de(request))
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        registrar(self.request.user, AccionAudit.CREAR, instance, ip=ip_de(self.request))

    def perform_update(self, serializer):
        campos = ",".join(sorted(serializer.validated_data.keys()))
        instance = serializer.save()
        # Solo NOMBRES de campos modificados en el log — nunca su contenido.
        registrar(
            self.request.user, AccionAudit.MODIFICAR, instance,
            campo=campos, ip=ip_de(self.request),
        )


class ConceptoViewSet(viewsets.ModelViewSet):
    """Concepto de aptitud: médico emite/firma; empresa_cliente solo lee firmados."""

    queryset = ConceptoMedicoOcupacional.objects.select_related(
        "atencion", "atencion__trabajador", "profesional"
    )
    serializer_class = ConceptoSerializer
    permission_classes = [PuedeVerConcepto]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = scope_conceptos(self.request.user, super().get_queryset())
        atencion_id = self.request.query_params.get("atencion")
        return qs.filter(atencion_id=atencion_id) if atencion_id else qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # La lectura del coordinador es la "excepción legal auditada" (§4).
        if request.user.rol in {Rol.COORDINADOR, Rol.EMPRESA_CLIENTE}:
            registrar(request.user, AccionAudit.VER, instance, ip=ip_de(request))
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        """Firma el concepto validando licencia SST vigente (regla 5)."""
        concepto = self.get_object()
        if concepto.firmado:
            return Response(
                {"detail": "El concepto ya está firmado."}, status=status.HTTP_409_CONFLICT
            )
        serializer = FirmarConceptoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        concepto.firmado = True
        concepto.licencia_sst = serializer.validated_data["licencia"]
        concepto.fecha_emision = timezone.now().date()
        concepto.save(update_fields=["firmado", "licencia_sst", "fecha_emision", "updated_at"])
        registrar(request.user, AccionAudit.MODIFICAR, concepto, campo="firmado", ip=ip_de(request))
        return Response(ConceptoSerializer(concepto).data)


# ---------------------------------------------------------------------------
# Módulo del médico: diagnósticos codificados, órdenes y recetas.
# Todos reservados al médico asignado a la atención (EsMedicoTratante).
# ---------------------------------------------------------------------------
class DiagnosticoViewSet(viewsets.ModelViewSet):
    """Diagnósticos CIE-10/CIE-11 de una historia. Solo el médico asignado."""

    serializer_class = DiagnosticoSerializer
    permission_classes = [EsMedicoTratante]

    def get_queryset(self):
        qs = Diagnostico.objects.filter(
            historia__atencion__profesional_asignado=self.request.user
        ).select_related("historia")
        atencion_id = self.request.query_params.get("atencion")
        return qs.filter(historia__atencion_id=atencion_id) if atencion_id else qs


class OrdenMedicaViewSet(viewsets.ModelViewSet):
    """Órdenes médicas (paraclínicos, procedimientos, remisiones, incapacidad)."""

    serializer_class = OrdenMedicaSerializer
    permission_classes = [EsMedicoTratante]

    def get_queryset(self):
        qs = OrdenMedica.objects.filter(
            atencion__profesional_asignado=self.request.user
        ).select_related("profesional")
        atencion_id = self.request.query_params.get("atencion")
        return qs.filter(atencion_id=atencion_id) if atencion_id else qs


class RecetaViewSet(viewsets.ModelViewSet):
    """Fórmulas médicas (recetas) con sus medicamentos. Solo el médico asignado."""

    serializer_class = RecetaSerializer
    permission_classes = [EsMedicoTratante]

    def get_queryset(self):
        qs = Receta.objects.filter(
            atencion__profesional_asignado=self.request.user
        ).select_related("profesional").prefetch_related("medicamentos")
        atencion_id = self.request.query_params.get("atencion")
        return qs.filter(atencion_id=atencion_id) if atencion_id else qs
