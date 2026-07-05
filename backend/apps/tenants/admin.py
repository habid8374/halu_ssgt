"""
Administración de IPS (tenants) y sus dominios.

SOLO visible desde el esquema público (dominio de administración, p. ej.
admin.localhost en dev). Desde el admin de una IPS estas entradas no
aparecen: una IPS no puede ver ni tocar el directorio de tenants.
"""
from django.contrib import admin
from django.db import connection
from django_tenants.utils import get_public_schema_name

from .models import IPS, Dominio


def _puede_gestionar_tenants(request) -> bool:
    """
    Visible en el esquema público (dominio de administración) o, mientras no
    exista dominio propio (un solo hostname en Railway), para SUPERUSUARIOS
    desde el admin de la IPS principal. Nunca para staff no-superusuario.
    """
    return connection.schema_name == get_public_schema_name() or request.user.is_superuser


class DominioInline(admin.TabularInline):
    model = Dominio
    extra = 1


@admin.register(IPS)
class IPSAdmin(admin.ModelAdmin):
    list_display = ("nombre", "schema_name", "nit", "codigo_reps", "activo", "created_on")
    search_fields = ("nombre", "nit", "schema_name")
    inlines = [DominioInline]

    def has_module_permission(self, request):
        return _puede_gestionar_tenants(request) and super().has_module_permission(request)


@admin.register(Dominio)
class DominioAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    search_fields = ("domain",)

    def has_module_permission(self, request):
        return _puede_gestionar_tenants(request) and super().has_module_permission(request)
