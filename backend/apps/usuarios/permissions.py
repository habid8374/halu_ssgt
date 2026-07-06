"""
Permisos DRF que implementan la matriz de roles de CLAUDE.md §4.

Principio: la seguridad se aplica en DOS capas, ambas obligatorias:
  1. Queryset scoping (get_queryset de cada vista usa los helpers scope_*):
     un rol nunca recibe filas que no le corresponden.
  2. has_object_permission: defensa en profundidad sobre el objeto puntual.

El rol empresa_cliente NUNCA alcanza historia clínica (regla 1); no hay
excepción posible en código: la clase PuedeVerHistoriaClinica lo niega
explícitamente antes de cualquier otra consideración.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .roles import Rol


# ---------------------------------------------------------------------------
# Helpers de scoping de queryset (capa 1)
# ---------------------------------------------------------------------------
def scope_atenciones(user, qs):
    """Filtra atenciones según el rol (tablero operativo, matriz §4)."""
    if user.rol == Rol.RECEPCION:
        return qs.filter(sede=user.sede)                    # todos, su sede
    if user.rol == Rol.MEDICO:
        return qs.filter(profesional_asignado=user)         # su cola
    if user.rol == Rol.COORDINADOR:
        return qs                                           # todas las sedes
    if user.rol == Rol.EMPRESA_CLIENTE:
        return qs.filter(empresa=user.empresa)              # solo p/ conceptos
    return qs.none()                                        # psicólogo, admin


def scope_historias(user, qs):
    """Historia clínica completa: SOLO médico y SOLO pacientes asignados."""
    if user.rol == Rol.MEDICO:
        return qs.filter(atencion__profesional_asignado=user)
    return qs.none()  # empresa_cliente, recepcion, coordinador, admin: nunca


def scope_conceptos(user, qs):
    """Concepto de aptitud: médico (los suyos) y empresa (sus trabajadores)."""
    if user.rol == Rol.MEDICO:
        return qs.filter(atencion__profesional_asignado=user)
    if user.rol == Rol.EMPRESA_CLIENTE:
        return qs.filter(atencion__empresa=user.empresa, firmado=True)
    if user.rol == Rol.COORDINADOR:
        # Excepción legal auditada: solo lectura y queda en AuditLog (regla 9).
        return qs
    return qs.none()


# ---------------------------------------------------------------------------
# Permisos por objeto (capa 2)
# ---------------------------------------------------------------------------
class BaseRolPermission(BasePermission):
    """Niega anónimos y usuarios sin rol; las subclases refinan."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol)


class PuedeVerTablero(BaseRolPermission):
    """Tablero operativo: recepción (su sede), médico (su cola), coordinador."""

    ROLES = {Rol.RECEPCION, Rol.MEDICO, Rol.COORDINADOR}

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol in self.ROLES

    def has_object_permission(self, request, view, obj):  # obj: Atencion
        user = request.user
        if user.rol == Rol.RECEPCION:
            return obj.sede_id == user.sede_id
        if user.rol == Rol.MEDICO:
            return obj.profesional_asignado_id == user.id or obj.sede_id == user.sede_id
        if user.rol == Rol.COORDINADOR:
            return True
        return False


class PuedeTransicionarAtencion(BaseRolPermission):
    """
    Cambio de estado de una atención:
      - recepción: en su sede (registrado→espera, llamado→espera).
      - médico: atenciones asignadas a él.
    """

    ROLES = {Rol.RECEPCION, Rol.MEDICO}

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol in self.ROLES

    def has_object_permission(self, request, view, obj):  # obj: Atencion
        user = request.user
        if user.rol == Rol.RECEPCION:
            return obj.sede_id == user.sede_id
        if user.rol == Rol.MEDICO:
            return obj.profesional_asignado_id == user.id
        return False


class PuedeVerHistoriaClinica(BaseRolPermission):
    """
    Historia clínica ocupacional (regla 1 — Res. 1843/2025):
    SOLO el médico y SOLO sobre pacientes asignados. Cualquier otro rol es
    denegado incondicionalmente — en particular empresa_cliente.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        # Denegación explícita e incondicional (no depende del objeto).
        if request.user.rol == Rol.EMPRESA_CLIENTE:
            return False
        return request.user.rol == Rol.MEDICO

    def has_object_permission(self, request, view, obj):  # obj: HistoriaClinicaOcupacional
        return (
            request.user.rol == Rol.MEDICO
            and obj.atencion.profesional_asignado_id == request.user.id
        )


class PuedeVerConcepto(BaseRolPermission):
    """
    Concepto médico ocupacional (documento que SÍ ve el empleador):
      - médico: los de sus pacientes asignados (lectura y escritura).
      - empresa_cliente: SOLO lectura, SOLO firmados, SOLO sus trabajadores.
      - coordinador: solo lectura (excepción legal, queda auditada).
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.rol == Rol.MEDICO:
            return True
        if request.user.rol in {Rol.EMPRESA_CLIENTE, Rol.COORDINADOR}:
            return request.method in SAFE_METHODS
        return False

    def has_object_permission(self, request, view, obj):  # obj: ConceptoMedicoOcupacional
        user = request.user
        if user.rol == Rol.MEDICO:
            return obj.atencion.profesional_asignado_id == user.id
        if user.rol == Rol.EMPRESA_CLIENTE:
            return (
                request.method in SAFE_METHODS
                and obj.firmado
                and obj.atencion.empresa_id == user.empresa_id
            )
        if user.rol == Rol.COORDINADOR:
            return request.method in SAFE_METHODS
        return False


class EsRecepcion(BaseRolPermission):
    """Admisión (crear atenciones, registrar trabajadores): solo recepción."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Rol.RECEPCION


class EsCoordinador(BaseRolPermission):
    """Administración de la IPS (personal, licencias): solo coordinador."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Rol.COORDINADOR


class EsMedicoTratante(BaseRolPermission):
    """
    Recursos clínicos derivados (diagnósticos, órdenes médicas, recetas):
    SOLO el médico asignado a la atención. Los objetos exponen la propiedad
    `medico_asignado_id` para verificarlo (defensa en profundidad, capa 2).
    """

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == Rol.MEDICO

    def has_object_permission(self, request, view, obj):
        return obj.medico_asignado_id == request.user.id


class GestionRecursosIPS(BaseRolPermission):
    """
    Recursos operativos de la IPS (sedes y consultorios):
      - Coordinador: administra (crea/edita).
      - Recepción y médico: solo lectura (los necesitan para admisión/tablero).
    """

    LECTORES = {Rol.RECEPCION, Rol.MEDICO, Rol.COORDINADOR}

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return request.user.rol in self.LECTORES
        return request.user.rol == Rol.COORDINADOR
