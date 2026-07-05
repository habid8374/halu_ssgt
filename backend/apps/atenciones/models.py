"""
Núcleo operativo: directorio de empresas/trabajadores, sedes/consultorios y
el ciclo de vida de la Atención con su historial de estados append-only.

Estos modelos alimentan el tablero de flujo en tiempo real (paso 5).
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Directorio de convenios y ubicaciones
# ---------------------------------------------------------------------------
class Empresa(models.Model):
    """Empresa cliente (convenio). NO es el tenant — el tenant es la IPS."""

    nombre = models.CharField(max_length=200)
    nit = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa (convenio)"
        verbose_name_plural = "Empresas (convenios)"
        constraints = [
            models.UniqueConstraint(fields=["nit"], name="uniq_empresa_nit")
        ]

    def __str__(self):
        return self.nombre


class Sede(models.Model):
    """Sede física de la IPS. El tablero se segmenta por sede."""

    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"

    def __str__(self):
        return self.nombre


class Consultorio(models.Model):
    """Consultorio dentro de una sede (segmenta el tablero a nivel fino)."""

    sede = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name="consultorios")
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Consultorio"
        verbose_name_plural = "Consultorios"

    def __str__(self):
        return f"{self.sede.nombre} — {self.nombre}"


class TipoDocumento(models.TextChoices):
    CC = "CC", "Cédula de ciudadanía"
    CE = "CE", "Cédula de extranjería"
    TI = "TI", "Tarjeta de identidad"
    PA = "PA", "Pasaporte"
    PEP = "PEP", "Permiso especial de permanencia"
    PPT = "PPT", "Permiso por protección temporal"


class Trabajador(models.Model):
    """
    Trabajador atendido (paciente). Pertenece a una Empresa (convenio).

    Retención (regla 2): no se elimina físicamente; se usa `archivado`.
    """

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="trabajadores")
    tipo_documento = models.CharField(max_length=4, choices=TipoDocumento.choices, default=TipoDocumento.CC)
    numero_documento = models.CharField(max_length=30)
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, blank=True)  # M/F/(otro), sin choices rígidos
    cargo = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    archivado = models.BooleanField(default=False)  # soft-delete (retención 15 años)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_documento", "numero_documento"],
                name="uniq_trabajador_documento",
            )
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.tipo_documento} {self.numero_documento})"


# ---------------------------------------------------------------------------
# Atención y máquina de estados
# ---------------------------------------------------------------------------
class EstadoAtencion(models.TextChoices):
    REGISTRADO = "registrado", "Registrado"
    ESPERA = "espera", "En espera"
    LLAMADO = "llamado", "Llamado"
    ATENCION = "atencion", "En atención"
    PARACLINICOS = "paraclinicos", "Paraclínicos"
    FINALIZADO = "finalizado", "Finalizado"


# Transiciones permitidas del tablero. Se valida en Atencion.cambiar_estado().
TRANSICIONES_VALIDAS = {
    EstadoAtencion.REGISTRADO: {EstadoAtencion.ESPERA},
    EstadoAtencion.ESPERA: {EstadoAtencion.LLAMADO},
    EstadoAtencion.LLAMADO: {EstadoAtencion.ATENCION, EstadoAtencion.ESPERA},  # no-show vuelve a espera
    EstadoAtencion.ATENCION: {EstadoAtencion.PARACLINICOS, EstadoAtencion.FINALIZADO},
    EstadoAtencion.PARACLINICOS: {EstadoAtencion.ATENCION, EstadoAtencion.FINALIZADO},
    EstadoAtencion.FINALIZADO: set(),  # estado terminal
}


class TipoExamen(models.TextChoices):
    """Tipos mínimos de evaluación médica ocupacional (Res. 1843/2025)."""

    PRE_INGRESO = "pre_ingreso", "Pre-ingreso"
    PERIODICO = "periodico", "Periódico"
    EGRESO = "egreso", "Egreso"
    POST_INCAPACIDAD = "post_incapacidad", "Post-incapacidad"
    RETORNO_LABORAL = "retorno_laboral", "Retorno laboral"
    SEGUIMIENTO = "seguimiento", "Seguimiento / control"


class TransicionInvalidaError(ValidationError):
    """Se intentó una transición de estado no permitida."""


class Atencion(models.Model):
    """
    Una atención (examen/consulta) de un trabajador. Unidad central del sistema.

    El cambio de estado SIEMPRE debe pasar por `cambiar_estado()`, que valida
    la transición y crea un HistorialEstado append-only.
    """

    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, related_name="atenciones")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="atenciones")
    sede = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name="atenciones")
    consultorio = models.ForeignKey(
        Consultorio, on_delete=models.SET_NULL, null=True, blank=True, related_name="atenciones"
    )

    tipo_examen = models.CharField(max_length=20, choices=TipoExamen.choices)
    estado = models.CharField(
        max_length=15, choices=EstadoAtencion.choices, default=EstadoAtencion.REGISTRADO, db_index=True
    )

    # Médico asignado (su "cola" en el tablero). Solo ve historia de sus asignados (§4).
    profesional_asignado = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="atenciones_asignadas",
        limit_choices_to={"rol": "medico"},
    )
    creado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="atenciones_creadas"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estado_actualizado_at = models.DateTimeField(default=timezone.now)  # base del semáforo de tiempos

    class Meta:
        verbose_name = "Atención"
        verbose_name_plural = "Atenciones"
        ordering = ["estado_actualizado_at"]
        indexes = [
            models.Index(fields=["sede", "estado"]),
            models.Index(fields=["profesional_asignado", "estado"]),
        ]

    def __str__(self):
        return f"Atención #{self.pk} — {self.trabajador} [{self.estado}]"

    def clean(self):
        # Coherencia empresa/trabajador.
        if self.trabajador_id and self.empresa_id and self.trabajador.empresa_id != self.empresa_id:
            raise ValidationError("La empresa de la atención no coincide con la del trabajador.")

    def cambiar_estado(self, nuevo_estado, usuario, nota=""):
        """
        Transiciona el estado validando la máquina de estados y registrando
        un HistorialEstado append-only. Devuelve el HistorialEstado creado.

        NO emite el evento de WebSocket aquí; eso lo hará la capa de servicio/
        signal en el paso 5 para no acoplar el modelo a Channels.
        """
        estado_anterior = self.estado
        if nuevo_estado == estado_anterior:
            raise TransicionInvalidaError(f"La atención ya está en estado '{estado_anterior}'.")
        if nuevo_estado not in TRANSICIONES_VALIDAS.get(estado_anterior, set()):
            raise TransicionInvalidaError(
                f"Transición no permitida: {estado_anterior} → {nuevo_estado}."
            )

        self.estado = nuevo_estado
        self.estado_actualizado_at = timezone.now()
        self.save(update_fields=["estado", "estado_actualizado_at", "updated_at"])

        return HistorialEstado.objects.create(
            atencion=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            nota=nota,
        )


class EstadoCita(models.TextChoices):
    PROGRAMADA = "programada", "Programada"
    CONFIRMADA = "confirmada", "Confirmada"
    CUMPLIDA = "cumplida", "Cumplida (admitida)"
    NO_ASISTIO = "no_asistio", "No asistió"
    CANCELADA = "cancelada", "Cancelada"


class Cita(models.Model):
    """
    Agenda de exámenes ocupacionales. Al llegar el trabajador, recepción la
    "admite": se crea la Atención (estado registrado) y la cita pasa a
    cumplida. La periodicidad de exámenes (recordatorios de vencimiento) se
    automatiza con Celery beat en una iteración posterior de la agenda.
    """

    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, related_name="citas")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="citas")
    sede = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name="citas")
    profesional_asignado = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, null=True, blank=True,
        related_name="citas_asignadas", limit_choices_to={"rol": "medico"},
    )
    tipo_examen = models.CharField(max_length=20, choices=TipoExamen.choices)
    fecha_hora = models.DateTimeField(db_index=True)
    estado = models.CharField(max_length=12, choices=EstadoCita.choices, default=EstadoCita.PROGRAMADA)
    nota = models.CharField(max_length=255, blank=True)
    atencion = models.OneToOneField(
        Atencion, on_delete=models.SET_NULL, null=True, blank=True, related_name="cita"
    )
    creado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="citas_creadas"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["fecha_hora"]

    def __str__(self):
        return f"Cita {self.trabajador} — {self.fecha_hora:%Y-%m-%d %H:%M} [{self.estado}]"


class HistorialEstado(models.Model):
    """
    Registro append-only de cada cambio de estado de una Atención
    (auditoría de flujo: timestamp + usuario). Regla 9: sin UPDATE/DELETE.
    """

    atencion = models.ForeignKey(Atencion, on_delete=models.PROTECT, related_name="historial_estados")
    estado_anterior = models.CharField(max_length=15, choices=EstadoAtencion.choices, blank=True)
    estado_nuevo = models.CharField(max_length=15, choices=EstadoAtencion.choices)
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.PROTECT, related_name="cambios_estado")
    nota = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"
        ordering = ["timestamp"]

    def __str__(self):
        return f"#{self.atencion_id}: {self.estado_anterior}→{self.estado_nuevo} @ {self.timestamp:%H:%M}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("HistorialEstado es append-only: no se puede modificar.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("HistorialEstado es append-only: no se puede eliminar.")
