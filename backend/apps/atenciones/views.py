from django.db import connection
from rest_framework import status, viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.permissions import (
    EsRecepcion,
    GestionRecursosIPS,
    PuedeTransicionarAtencion,
    PuedeVerTablero,
    scope_atenciones,
)
from apps.usuarios.roles import Rol

from .models import (
    Atencion,
    Cita,
    ConfiguracionIPS,
    Consultorio,
    Empresa,
    Profesiograma,
    PruebaAtencion,
    Sede,
    Trabajador,
    TransicionInvalidaError,
)
from .serializers import (
    AtencionSerializer,
    CitaSerializer,
    ConfiguracionIPSSerializer,
    ConsultorioSerializer,
    CrearAtencionSerializer,
    EmpresaSerializer,
    HistorialEstadoSerializer,
    ProfesiogramaSerializer,
    PruebaAtencionSerializer,
    SedeSerializer,
    TrabajadorSerializer,
    TransicionSerializer,
)
from .services import difundir_atencion_creada, transicionar_atencion


class ConfiguracionIPSView(APIView):
    """
    Membrete de la IPS para los documentos. Lectura para cualquier usuario
    autenticado (lo necesitan médico y empresa al imprimir); edición solo del
    coordinador. Singleton por esquema; se auto-rellena con los datos del
    tenant la primera vez.
    """

    def _obtener(self):
        cfg = ConfiguracionIPS.objects.first()
        if cfg is None:
            tenant = getattr(connection, "tenant", None)
            cfg = ConfiguracionIPS.objects.create(
                razon_social=getattr(tenant, "nombre", "") or "",
                nit=getattr(tenant, "nit", "") or "",
                codigo_habilitacion=getattr(tenant, "codigo_reps", "") or "",
            )
        return cfg

    def get(self, request):
        if not (request.user and request.user.is_authenticated and request.user.rol):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(ConfiguracionIPSSerializer(self._obtener()).data)

    def patch(self, request):
        if not (request.user and request.user.is_authenticated and request.user.rol == Rol.COORDINADOR):
            return Response({"detail": "Solo el coordinador configura la IPS."}, status=status.HTTP_403_FORBIDDEN)
        cfg = self._obtener()
        serializer = ConfiguracionIPSSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SedeViewSet(viewsets.ModelViewSet):
    """
    Sedes de la IPS. El coordinador las crea/edita desde la app; recepción y
    médico solo las consultan. Sin DELETE: se desactivan (`activa`).
    """

    serializer_class = SedeSerializer
    permission_classes = [GestionRecursosIPS]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Sede.objects.order_by("nombre")
        # El coordinador administra todas; los demás solo ven las activas.
        if self.request.user.rol != Rol.COORDINADOR:
            qs = qs.filter(activa=True)
        return qs


class ConsultorioViewSet(viewsets.ModelViewSet):
    """Consultorios por sede. Coordinador administra; operativos consultan."""

    serializer_class = ConsultorioSerializer
    permission_classes = [GestionRecursosIPS]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Consultorio.objects.select_related("sede").order_by("sede__nombre", "nombre")
        if self.request.user.rol != Rol.COORDINADOR:
            qs = qs.filter(activo=True)
        sede_id = self.request.query_params.get("sede")
        return qs.filter(sede_id=sede_id) if sede_id else qs


class PermisoEmpresas(BasePermission):
    """Coordinador gestiona los convenios; recepción solo los consulta."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.rol == Rol.COORDINADOR:
            return True
        return u.rol == Rol.RECEPCION and request.method in SAFE_METHODS


class EmpresaViewSet(viewsets.ModelViewSet):
    """
    Empresas con convenio. Cada IPS crea y administra las suyas desde la app
    (regla de UX: nada exige el admin para operar). Sin DELETE: se desactivan.
    """

    queryset = Empresa.objects.order_by("nombre")
    serializer_class = EmpresaSerializer
    permission_classes = [PermisoEmpresas]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Recepción solo ve activas (para admisión); coordinador ve todas.
        if self.request.user.rol == Rol.RECEPCION:
            qs = qs.filter(activo=True)
        return qs


class MedicoViewSet(viewsets.ViewSet):
    """Médicos activos de la sede (para asignar la atención en admisión)."""

    permission_classes = [EsRecepcion]

    def list(self, request):
        from apps.usuarios.models import Usuario

        medicos = Usuario.objects.filter(
            rol=Rol.MEDICO, is_active=True, sede=request.user.sede
        ).order_by("nombre_completo")
        return Response(
            [{"id": m.id, "nombre_completo": m.nombre_completo} for m in medicos]
        )


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
        ).prefetch_related("pruebas")
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

    @action(detail=True, methods=["get"])
    def sugerir_concepto(self, request, pk=None):
        """
        Sugiere el concepto de aptitud compilando los diagnósticos y los
        resúmenes de las pruebas del circuito. La decisión final es del médico.
        """
        if request.user.rol != Rol.MEDICO:
            return Response(status=status.HTTP_403_FORBIDDEN)
        atencion = self.get_object()
        from apps.historia_clinica.models import Diagnostico

        diags = list(
            Diagnostico.objects.filter(historia__atencion=atencion).values_list("cie10_codigo", "cie10_desc")
        )
        pruebas = list(atencion.pruebas.all())
        resumenes = [f"{p.get_tipo_prueba_display()}: {p.resumen}" for p in pruebas if p.resumen]

        # Heurística: si hay diagnósticos o hallazgos, sugerir "con restricciones".
        hay_hallazgo = bool(diags) or any(
            kw in (p.resumen or "").lower()
            for p in pruebas for kw in ("hipoacusia", "alterad", "obstructiv", "restrictiv", "mixto")
        )
        aptitud = "apto_restricciones" if hay_hallazgo else "apto"
        restricciones = "; ".join(desc for _, desc in diags)
        recomendaciones = " | ".join(resumenes)
        return Response({
            "aptitud": aptitud,
            "restricciones": restricciones,
            "recomendaciones_laborales": recomendaciones,
            "diagnosticos": [{"codigo": c, "descripcion": d} for c, d in diags],
        })

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
        # Aparece en tiempo real en el tablero de toda la sede.
        difundir_atencion_creada(atencion)
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
    def rda(self, request, pk=None):
        """
        Resumen Digital de Atención (FHIR Bundle, Res. 866/2021 — fase 4).
        Médico asignado o coordinador; la generación queda auditada.
        """
        from apps.historia_clinica.rda import construir_rda
        from apps.usuarios.audit import ip_de, registrar
        from apps.usuarios.models import AccionAudit

        if request.user.rol not in {Rol.MEDICO, Rol.COORDINADOR}:
            return Response(status=status.HTTP_403_FORBIDDEN)
        atencion = self.get_object()
        registrar(request.user, AccionAudit.EXPORTAR, atencion, descripcion="RDA", ip=ip_de(request))
        return Response(construir_rda(atencion))

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        atencion = self.get_object()
        data = HistorialEstadoSerializer(
            atencion.historial_estados.select_related("usuario"), many=True
        ).data
        return Response(data)


class CitaViewSet(viewsets.ModelViewSet):
    """
    Agenda. Recepción gestiona las citas de su sede; el médico ve las suyas;
    el coordinador ve todas (solo lectura vía permisos de tablero).
    """

    queryset = Cita.objects.select_related(
        "trabajador", "empresa", "profesional_asignado"
    )
    serializer_class = CitaSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "partial_update", "admitir", "cancelar"}:
            return [EsRecepcion()]
        return [PuedeVerTablero()]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.rol == Rol.RECEPCION:
            qs = qs.filter(sede=user.sede)
        elif user.rol == Rol.MEDICO:
            qs = qs.filter(profesional_asignado=user)
        elif user.rol != Rol.COORDINADOR:
            return qs.none()
        if self.request.query_params.get("pendientes") == "1":
            qs = qs.filter(estado__in=["programada", "confirmada"])
        return qs

    @action(detail=True, methods=["post"])
    def admitir(self, request, pk=None):
        """Llegó el trabajador: crea la Atención y marca la cita cumplida."""
        cita = self.get_object()
        if cita.estado in {"cumplida", "cancelada"}:
            return Response(
                {"detail": f"La cita ya está {cita.estado}."}, status=status.HTTP_409_CONFLICT
            )
        atencion = Atencion.objects.create(
            trabajador=cita.trabajador, empresa=cita.empresa, sede=cita.sede,
            tipo_examen=cita.tipo_examen, profesional_asignado=cita.profesional_asignado,
            creado_por=request.user,
        )
        cita.estado = "cumplida"
        cita.atencion = atencion
        cita.save(update_fields=["estado", "atencion"])
        # El paciente activado desde agenda aparece en el tablero en tiempo real.
        difundir_atencion_creada(atencion)
        return Response(AtencionSerializer(atencion).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        cita = self.get_object()
        if cita.estado == "cumplida":
            return Response({"detail": "La cita ya fue admitida."}, status=status.HTTP_409_CONFLICT)
        cita.estado = "cancelada"
        cita.save(update_fields=["estado"])
        return Response(CitaSerializer(cita).data)


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


# ---------------------------------------------------------------------------
# Profesiogramas (batería por empresa/cargo) y pruebas del circuito
# ---------------------------------------------------------------------------
class ProfesiogramaViewSet(viewsets.ModelViewSet):
    """
    Profesiogramas: el coordinador define la batería de pruebas por empresa y
    cargo; recepción los consulta en la admisión. Sin DELETE físico salvo por
    el coordinador (se puede desactivar con `activo`).
    """

    serializer_class = ProfesiogramaSerializer
    permission_classes = [GestionRecursosIPS]

    def get_queryset(self):
        qs = Profesiograma.objects.select_related("empresa").prefetch_related("pruebas", "examenes").order_by("empresa__nombre", "cargo")
        empresa = self.request.query_params.get("empresa")
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        return qs

    @action(detail=False, methods=["get"])
    def resolver(self, request):
        """Batería de pruebas para una empresa + cargo (previsualización)."""
        empresa = request.query_params.get("empresa")
        cargo = (request.query_params.get("cargo") or "").strip()
        prof = (
            Profesiograma.objects.filter(empresa_id=empresa, cargo__iexact=cargo, activo=True)
            .prefetch_related("pruebas").first()
            if empresa else None
        )
        pruebas = [{"tipo_prueba": p.tipo_prueba, "detalle": p.detalle} for p in prof.pruebas.all()] if prof else []
        return Response({"encontrado": bool(prof), "cargo": cargo, "pruebas": pruebas})


class PuedeGestionarPruebas(BasePermission):
    """
    Estaciones del circuito: recepción (triaje de su sede), médico (sus
    atenciones), psicólogo y coordinador. Empresa_cliente nunca.
    """

    ROLES = {Rol.RECEPCION, Rol.MEDICO, Rol.PSICOLOGO_SST, Rol.COORDINADOR}

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.rol in self.ROLES)


class PruebaAtencionViewSet(viewsets.ModelViewSet):
    """Pruebas/estaciones de una atención: estado + resultado (digitar/adjuntar)."""

    serializer_class = PruebaAtencionSerializer
    permission_classes = [PuedeGestionarPruebas]

    def get_queryset(self):
        u = self.request.user
        qs = PruebaAtencion.objects.select_related("atencion").order_by("created_at")
        if u.rol == Rol.RECEPCION:
            qs = qs.filter(atencion__sede=u.sede)
        elif u.rol == Rol.MEDICO:
            qs = qs.filter(atencion__profesional_asignado=u)
        # coordinador y psicólogo: dentro del tenant (sin filtro extra aquí).
        atencion_id = self.request.query_params.get("atencion")
        return qs.filter(atencion_id=atencion_id) if atencion_id else qs

    def perform_update(self, serializer):
        from django.utils import timezone

        datos = serializer.validated_data
        extra = {}
        if datos.get("estado") == "realizada" and not serializer.instance.realizada_at:
            extra = {"realizada_por": self.request.user, "realizada_at": timezone.now()}
        serializer.save(**extra)
