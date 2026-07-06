"""
Usuarios del sistema, profesionales con licencia SST, y auditoría inmutable.

Vive en el esquema de cada IPS (TENANT_APPS): cada IPS tiene su propio
directorio de usuarios.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .managers import UsuarioManager
from .roles import Rol


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Usuario autenticable. El campo `rol` gobierna el acceso (matriz §4).

    Ámbito (scoping) según rol:
      - medico / recepcion / psicologo_sst -> ligados a una `sede`.
      - empresa_cliente -> ligado a una `empresa` (solo ve sus trabajadores).
      - coordinador / admin_sistema -> sin scope de sede (transversal).
    """

    email = models.EmailField(unique=True)
    nombre_completo = models.CharField(max_length=200)
    rol = models.CharField(max_length=20, choices=Rol.choices)

    # Scoping para queryset-level security (se aplica en permisos DRF).
    sede = models.ForeignKey(
        "atenciones.Sede",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        help_text="Sede a la que pertenece (recepción, médico, psicólogo).",
    )
    empresa = models.ForeignKey(
        "atenciones.Empresa",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios_portal",
        help_text="Empresa cliente asociada (solo rol empresa_cliente).",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo"]

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.nombre_completo} <{self.email}> [{self.rol}]"

    def clean(self):
        # Coherencia de scope según rol.
        if self.rol == Rol.EMPRESA_CLIENTE and self.empresa_id is None:
            raise ValidationError("empresa_cliente requiere una empresa asociada.")
        if self.rol in {Rol.RECEPCION, Rol.MEDICO, Rol.TECNICO, Rol.PSICOLOGO_SST} and self.sede_id is None:
            raise ValidationError("Este rol requiere una sede asociada.")


class TipoProfesional(models.TextChoices):
    MEDICO = "medico", "Médico ocupacional"
    PSICOLOGO = "psicologo", "Psicólogo SST"


class Profesional(models.Model):
    """
    Datos profesionales de un usuario clínico (médico o psicólogo).

    Regla 5 (CLAUDE.md): quien firma un ConceptoMedicoOcupacional debe tener
    una LicenciaSST vigente. El modelo lo soporta; la validación de firma se
    aplica en la capa de servicios/serializers al emitir el concepto.
    """

    usuario = models.OneToOneField(
        Usuario, on_delete=models.PROTECT, related_name="profesional"
    )
    tipo = models.CharField(max_length=15, choices=TipoProfesional.choices)
    # Registro médico / tarjeta profesional (RETHUS — validación automática fase 2).
    registro_profesional = models.CharField(max_length=50, blank=True)
    especialidad = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Profesional"
        verbose_name_plural = "Profesionales"

    def __str__(self):
        return f"{self.usuario.nombre_completo} ({self.tipo})"

    @property
    def tiene_licencia_vigente(self) -> bool:
        hoy = timezone.now().date()
        return self.licencias.filter(
            validada=True, fecha_vencimiento__gte=hoy
        ).exists()


class LicenciaSST(models.Model):
    """
    Licencia en Seguridad y Salud en el Trabajo (Res. 4502/2012).

    Obligatoria y vigente para practicar exámenes / firmar conceptos.
    """

    profesional = models.ForeignKey(
        Profesional, on_delete=models.PROTECT, related_name="licencias"
    )
    numero = models.CharField(max_length=50)
    entidad_expide = models.CharField(max_length=150)
    fecha_expedicion = models.DateField()
    fecha_vencimiento = models.DateField()
    # `validada`: verificación (manual en fase 1, RETHUS en fase 2).
    validada = models.BooleanField(default=False)
    validada_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Licencia SST"
        verbose_name_plural = "Licencias SST"
        constraints = [
            models.UniqueConstraint(
                fields=["profesional", "numero"], name="uniq_licencia_por_profesional"
            )
        ]

    def __str__(self):
        return f"Licencia {self.numero} — {self.profesional}"

    @property
    def vigente(self) -> bool:
        return self.validada and self.fecha_vencimiento >= timezone.now().date()


# ---------------------------------------------------------------------------
# Auditoría inmutable (CLAUDE.md regla 9 / §8)
# ---------------------------------------------------------------------------
class AccionAudit(models.TextChoices):
    VER = "ver", "Lectura"
    CREAR = "crear", "Creación"
    MODIFICAR = "modificar", "Modificación"
    EXPORTAR = "exportar", "Exportación"


class AppendOnlyError(Exception):
    """Se intentó modificar o borrar un registro append-only."""


class AuditLog(models.Model):
    """
    Log inmutable de accesos/cambios sobre historia clínica y datos sensibles.

    Append-only: no se permite UPDATE ni DELETE (regla 9). Nunca guarda el
    contenido clínico, solo metadatos (quién, qué, cuándo, sobre qué registro
    y opcionalmente qué campo).
    """

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,  # no se borran usuarios con auditoría asociada
        related_name="eventos_auditoria",
        null=True,
    )
    accion = models.CharField(max_length=12, choices=AccionAudit.choices)
    modelo = models.CharField(max_length=100, help_text="Ej. historia_clinica.HistoriaClinicaOcupacional")
    objeto_id = models.CharField(max_length=64)
    campo = models.CharField(max_length=100, blank=True)
    descripcion = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.usuario_id} {self.accion} {self.modelo}#{self.objeto_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise AppendOnlyError("AuditLog es append-only: no se puede modificar.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError("AuditLog es append-only: no se puede eliminar.")
