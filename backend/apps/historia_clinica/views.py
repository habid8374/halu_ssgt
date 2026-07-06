import csv
import io

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.audit import ip_de, registrar
from apps.usuarios.models import AccionAudit
from apps.usuarios.permissions import (
    EsMedicoTratante,
    GestionRecursosIPS,
    PuedeVerConcepto,
    PuedeVerHistoriaClinica,
    scope_conceptos,
    scope_historias,
)
from apps.usuarios.roles import Rol

from .models import (
    CodigoCups,
    ConceptoMedicoOcupacional,
    Diagnostico,
    HistoriaClinicaOcupacional,
    OrdenMedica,
    Receta,
)
from .serializers import (
    CodigoCupsSerializer,
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


def _parsear_cups(texto: str):
    """
    Extrae (codigo, nombre, seccion) de un CSV del CUPS oficial. Tolera
    delimitadores «;», «,» o tab, con o sin encabezado, y toma el código de la
    primera columna y la descripción de la segunda (sección opcional, tercera).
    """
    muestra = texto[:4096]
    try:
        delim = csv.Sniffer().sniff(muestra, delimiters=";,\t|").delimiter
    except csv.Error:
        delim = ";" if muestra.count(";") >= muestra.count(",") else ","
    filas = []
    for cols in csv.reader(io.StringIO(texto), delimiter=delim):
        if len(cols) < 2:
            continue
        codigo = cols[0].strip().strip('"').replace(" ", "")
        nombre = cols[1].strip().strip('"')
        # Descarta encabezados o filas sin código alfanumérico plausible.
        if not codigo or not nombre or not any(ch.isdigit() for ch in codigo):
            continue
        if len(codigo) > 10:
            continue
        seccion = cols[2].strip().strip('"') if len(cols) > 2 else ""
        filas.append((codigo, nombre[:255], seccion[:120]))
    return filas


class CupsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Catálogo CUPS buscable (procedimientos/paraclínicos). Lectura para los
    roles operativos; el coordinador importa el archivo oficial del SISPRO
    con la acción `importar` (upsert por código, sin comandos).
    """

    serializer_class = CodigoCupsSerializer
    permission_classes = [GestionRecursosIPS]

    def get_queryset(self):
        qs = CodigoCups.objects.filter(activo=True)
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(codigo__startswith=q)
        return qs.distinct()[:50]

    @action(detail=False, methods=["post"])
    def importar(self, request):
        """Carga masiva del CUPS oficial (CSV). Solo coordinador."""
        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response({"detail": "Adjunta el archivo CSV del CUPS."},
                            status=status.HTTP_400_BAD_REQUEST)
        raw = archivo.read()
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                texto = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return Response({"detail": "No se pudo leer el archivo (codificación)."},
                            status=status.HTTP_400_BAD_REQUEST)

        filas = _parsear_cups(texto)
        if not filas:
            return Response({"detail": "No se reconocieron filas de CUPS en el archivo."},
                            status=status.HTTP_400_BAD_REQUEST)

        existentes = {c.codigo: c for c in CodigoCups.objects.all()}
        crear, actualizar = [], []
        vistos = set()
        for codigo, nombre, seccion in filas:
            if codigo in vistos:
                continue
            vistos.add(codigo)
            actual = existentes.get(codigo)
            if actual is None:
                crear.append(CodigoCups(codigo=codigo, nombre=nombre, seccion=seccion, activo=True))
            elif actual.nombre != nombre or actual.seccion != seccion or not actual.activo:
                actual.nombre, actual.seccion, actual.activo = nombre, seccion, True
                actualizar.append(actual)
        CodigoCups.objects.bulk_create(crear, batch_size=1000, ignore_conflicts=True)
        if actualizar:
            CodigoCups.objects.bulk_update(actualizar, ["nombre", "seccion", "activo"], batch_size=1000)
        return Response({
            "creados": len(crear), "actualizados": len(actualizar),
            "total": CodigoCups.objects.count(),
        })
