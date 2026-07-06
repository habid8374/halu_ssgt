"""
Admin operativo del tenant. El estado de la Atención NO se edita aquí:
solo cambia vía la máquina de estados (API /transicion/), que valida y
deja historial. El HistorialEstado es de solo lectura (append-only).
"""
from django.contrib import admin

from .models import (
    Atencion,
    Cita,
    Consultorio,
    Empresa,
    HistorialEstado,
    Profesiograma,
    Sede,
    TipoExamenRequerido,
    Trabajador,
)


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "activa")


@admin.register(Consultorio)
class ConsultorioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "sede", "activo")
    list_filter = ("sede",)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "activo")
    search_fields = ("nombre", "nit")


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ("primer_nombre", "primer_apellido", "tipo_documento", "numero_documento", "empresa", "cargo", "archivado")
    list_filter = ("empresa", "archivado")
    search_fields = ("primer_nombre", "primer_apellido", "numero_documento")

    def has_delete_permission(self, request, obj=None):
        # Retención 15 años (regla 2): archivar, nunca borrar.
        return False


@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ("id", "trabajador", "empresa", "sede", "tipo_examen", "estado", "profesional_asignado", "created_at")
    list_filter = ("estado", "sede", "tipo_examen")
    readonly_fields = ("estado", "estado_actualizado_at", "created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("atencion", "estado_anterior", "estado_nuevo", "usuario", "timestamp")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ExamenRequeridoInline(admin.TabularInline):
    model = TipoExamenRequerido
    extra = 1


@admin.register(Profesiograma)
class ProfesiogramaAdmin(admin.ModelAdmin):
    list_display = ("empresa", "cargo", "activo")
    list_filter = ("empresa",)
    inlines = [ExamenRequeridoInline]


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "fecha_hora", "tipo_examen", "estado", "profesional_asignado")
    list_filter = ("estado",)
