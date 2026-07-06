"""
Roles del sistema (matriz de CLAUDE.md §4).

Estos identificadores son la fuente de verdad usada por los permisos DRF a
nivel de objeto (has_object_permission). No renombrar sin migrar datos.
"""
from django.db import models


class Rol(models.TextChoices):
    RECEPCION = "recepcion", "Recepción / Admisión"
    MEDICO = "medico", "Médico ocupacional"
    TECNICO = "tecnico", "Técnico de apoyo diagnóstico"
    PSICOLOGO_SST = "psicologo_sst", "Psicólogo SST"
    COORDINADOR = "coordinador", "Coordinador / Gerencia IPS"
    EMPRESA_CLIENTE = "empresa_cliente", "Empresa cliente (portal externo)"
    ADMIN_SISTEMA = "admin_sistema", "Administrador de sistema"
