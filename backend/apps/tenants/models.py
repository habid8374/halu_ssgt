"""
Modelo de tenant: un esquema PostgreSQL por IPS (decisión confirmada).

La IPS es el cliente SaaS. Sus Sedes y Consultorios son modelos DENTRO del
esquema (ver apps.atenciones), de modo que el coordinador puede consultar
"todas las sedes" y los reportes agregados en una sola query, y el tablero
filtra por sede/consultorio sin cruzar esquemas.
"""
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class IPS(TenantMixin):
    """Institución Prestadora de Servicios de salud ocupacional (tenant)."""

    nombre = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, unique=True)
    # Código de habilitación en el REPS (Res. 3100/2019). Validación manual en fase 1.
    codigo_reps = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    # django-tenants crea/borra el esquema automáticamente al guardar/eliminar.
    auto_create_schema = True

    class Meta:
        verbose_name = "IPS"
        verbose_name_plural = "IPS"

    def __str__(self):
        return f"{self.nombre} ({self.schema_name})"


class Dominio(DomainMixin):
    """Dominio/subdominio que enruta hacia el esquema de una IPS."""

    pass
