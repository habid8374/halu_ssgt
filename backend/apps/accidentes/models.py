"""
Gestión de accidentes de trabajo y enfermedad laboral (fase 2).

- AccidenteTrabajo: el evento (Res. 1401/2007).
- InvestigacionAccidente: investigación obligatoria (15 días si es mortal).
- ReporteFURAT / ReporteFUREL: reporte a la ARL en máximo 2 DÍAS HÁBILES
  (regla 6, CLAUDE.md). El plazo se calcula al crear el reporte y Celery
  beat genera alertas cuando se acerca o vence (ver tasks.py).
- Alerta: bandeja de alertas de cumplimiento del tenant (plazos FURAT/FUREL
  y 20 días hábiles de adaptación de recomendaciones, regla 7).

RIPS/MUV/Factus NO se toca aquí: llega en fase 3 acoplado solo a este módulo.
"""
from django.db import models
from django.utils import timezone

from .utils import sumar_dias_habiles


class GravedadAccidente(models.TextChoices):
    LEVE = "leve", "Leve"
    GRAVE = "grave", "Grave"
    MORTAL = "mortal", "Mortal"


class TipoEvento(models.TextChoices):
    ACCIDENTE = "accidente", "Accidente de trabajo (FURAT)"
    ENFERMEDAD = "enfermedad", "Enfermedad laboral (FUREL)"


class AccidenteTrabajo(models.Model):
    tipo_evento = models.CharField(max_length=12, choices=TipoEvento.choices, default=TipoEvento.ACCIDENTE)
    trabajador = models.ForeignKey("atenciones.Trabajador", on_delete=models.PROTECT, related_name="accidentes")
    empresa = models.ForeignKey("atenciones.Empresa", on_delete=models.PROTECT, related_name="accidentes")
    sede = models.ForeignKey("atenciones.Sede", on_delete=models.PROTECT, related_name="accidentes", null=True, blank=True)
    fecha_evento = models.DateField()
    gravedad = models.CharField(max_length=8, choices=GravedadAccidente.choices, default=GravedadAccidente.LEVE)
    descripcion = models.TextField()
    arl_nombre = models.CharField(max_length=120, blank=True)
    registrado_por = models.ForeignKey("usuarios.Usuario", on_delete=models.PROTECT, related_name="accidentes_registrados")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Accidente / enfermedad laboral"
        verbose_name_plural = "Accidentes / enfermedades laborales"
        ordering = ["-fecha_evento"]

    def __str__(self):
        return f"{self.get_tipo_evento_display()} — {self.trabajador} ({self.fecha_evento})"


class InvestigacionAccidente(models.Model):
    """Investigación (Res. 1401/2007): 15 días calendario; obligatoria si es grave/mortal."""

    accidente = models.OneToOneField(AccidenteTrabajo, on_delete=models.PROTECT, related_name="investigacion")
    fecha_limite = models.DateField()
    completada = models.BooleanField(default=False)
    conclusiones = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Investigación de accidente"
        verbose_name_plural = "Investigaciones de accidente"

    def __str__(self):
        return f"Investigación de {self.accidente_id} (límite {self.fecha_limite})"


class EstadoReporte(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente de envío"
    ENVIADO = "enviado", "Enviado a la ARL"


class ReporteARLBase(models.Model):
    """Base común FURAT/FUREL: plazo de 2 días hábiles desde el evento."""

    PLAZO_DIAS_HABILES = 2

    accidente = models.OneToOneField(AccidenteTrabajo, on_delete=models.PROTECT, related_name="+")
    estado = models.CharField(max_length=10, choices=EstadoReporte.choices, default=EstadoReporte.PENDIENTE)
    fecha_limite = models.DateField()
    enviado_at = models.DateTimeField(null=True, blank=True)
    radicado_arl = models.CharField(max_length=60, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.fecha_limite:
            self.fecha_limite = sumar_dias_habiles(
                self.accidente.fecha_evento, self.PLAZO_DIAS_HABILES
            )
        return super().save(*args, **kwargs)

    def marcar_enviado(self, radicado=""):
        self.estado = EstadoReporte.ENVIADO
        self.enviado_at = timezone.now()
        self.radicado_arl = radicado
        self.save(update_fields=["estado", "enviado_at", "radicado_arl"])


class ReporteFURAT(ReporteARLBase):
    accidente = models.OneToOneField(AccidenteTrabajo, on_delete=models.PROTECT, related_name="furat")

    class Meta:
        verbose_name = "Reporte FURAT"
        verbose_name_plural = "Reportes FURAT"


class ReporteFUREL(ReporteARLBase):
    accidente = models.OneToOneField(AccidenteTrabajo, on_delete=models.PROTECT, related_name="furel")

    class Meta:
        verbose_name = "Reporte FUREL"
        verbose_name_plural = "Reportes FUREL"


class TipoAlerta(models.TextChoices):
    FURAT = "furat", "Plazo FURAT (2 días hábiles)"
    FUREL = "furel", "Plazo FUREL (2 días hábiles)"
    ADAPTACION = "adaptacion", "Adaptación de condiciones (20 días hábiles)"
    INVESTIGACION = "investigacion", "Plazo de investigación"


class Alerta(models.Model):
    """
    Alerta de plazo normativo generada por Celery beat (tasks.revisar_plazos).
    Única por (tipo, referencia) — el task no duplica alertas abiertas.
    """

    tipo = models.CharField(max_length=15, choices=TipoAlerta.choices)
    referencia_modelo = models.CharField(max_length=60)
    referencia_id = models.CharField(max_length=30)
    mensaje = models.CharField(max_length=255)
    vence = models.DateField()
    vencida = models.BooleanField(default=False)
    resuelta = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alerta de plazo"
        verbose_name_plural = "Alertas de plazo"
        ordering = ["resuelta", "vence"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "referencia_modelo", "referencia_id"],
                name="uniq_alerta_por_referencia",
            )
        ]

    def __str__(self):
        return f"[{self.tipo}] {self.mensaje} (vence {self.vence})"
