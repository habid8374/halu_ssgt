"""
Admin de usuarios/profesionales del tenant. El AuditLog es de solo lectura
(append-only, regla 9): sin agregar, editar ni borrar desde el admin.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, LicenciaSST, Profesional, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "nombre_completo", "rol", "sede", "empresa", "is_active")
    list_filter = ("rol", "is_active")
    search_fields = ("email", "nombre_completo")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identidad", {"fields": ("nombre_completo",)}),
        ("Rol y ámbito", {"fields": ("rol", "sede", "empresa")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nombre_completo", "rol", "sede", "empresa",
                       "password1", "password2"),
        }),
    )


class LicenciaInline(admin.TabularInline):
    model = LicenciaSST
    extra = 0


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "registro_profesional", "tiene_licencia_vigente")
    inlines = [LicenciaInline]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "usuario", "accion", "modelo", "objeto_id", "campo", "ip")
    list_filter = ("accion",)
    search_fields = ("modelo", "objeto_id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
