"""
Facturación — DOS MOTORES SEPARADOS (regla 8, CLAUDE.md):

1. Motor ESTÁNDAR (este bloque superior): factura a la empresa cliente por
   exámenes ocupacionales (ingreso, periódico, egreso, batería…). Fuera del
   SGSSS: NUNCA genera RIPS (Res. 948/2026 excluye la medicina ocupacional
   pagada por el empleador).

2. Motor ARL/RIPS (FacturaARL): SOLO para atenciones derivadas de un
   accidente de trabajo / enfermedad laboral facturadas a la ARL. Es el
   único punto del sistema que genera RIPS. Si la IPS no atiende accidentes,
   simplemente no usa este módulo.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Motor estándar (empresas cliente — sin RIPS)
# ---------------------------------------------------------------------------
class TarifaConvenio(models.Model):
    """Valor pactado por tipo de examen dentro del convenio con la empresa."""

    empresa = models.ForeignKey("atenciones.Empresa", on_delete=models.PROTECT, related_name="tarifas")
    tipo_examen = models.CharField(max_length=20)
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Tarifa de convenio"
        verbose_name_plural = "Tarifas de convenio"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "tipo_examen"], name="uniq_tarifa_empresa_examen")
        ]

    def __str__(self):
        return f"{self.empresa.nombre} · {self.tipo_examen}: ${self.valor}"


class EstadoFactura(models.TextChoices):
    BORRADOR = "borrador", "Borrador"
    EMITIDA = "emitida", "Emitida"
    PAGADA = "pagada", "Pagada"
    ANULADA = "anulada", "Anulada"


class Factura(models.Model):
    """Factura estándar a empresa cliente. No genera RIPS jamás."""

    empresa = models.ForeignKey("atenciones.Empresa", on_delete=models.PROTECT, related_name="facturas")
    numero = models.CharField(max_length=20, blank=True)  # se asigna al emitir
    periodo_desde = models.DateField()
    periodo_hasta = models.DateField()
    estado = models.CharField(max_length=10, choices=EstadoFactura.choices, default=EstadoFactura.BORRADOR)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    creada_por = models.ForeignKey("usuarios.Usuario", on_delete=models.PROTECT, related_name="facturas_creadas")
    emitida_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Factura (empresa)"
        verbose_name_plural = "Facturas (empresas)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Factura {self.numero or f'borrador #{self.pk}'} — {self.empresa.nombre} (${self.total})"

    def emitir(self):
        if self.estado != EstadoFactura.BORRADOR:
            raise ValidationError(f"Solo se emite un borrador (estado actual: {self.estado}).")
        self.numero = f"FE-{self.pk:06d}"
        self.estado = EstadoFactura.EMITIDA
        self.emitida_at = timezone.now()
        self.save(update_fields=["numero", "estado", "emitida_at"])


class FacturaItem(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="items")
    atencion = models.OneToOneField(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="factura_item",
        null=True, blank=True,
    )
    descripcion = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Ítem de factura"
        verbose_name_plural = "Ítems de factura"

    def __str__(self):
        return f"{self.descripcion} (${self.valor})"


# ---------------------------------------------------------------------------
# Motor ARL/RIPS (SOLO accidentes de trabajo / enfermedad laboral)
# ---------------------------------------------------------------------------
class EstadoFacturaARL(models.TextChoices):
    BORRADOR = "borrador", "Borrador (RIPS generado)"
    VALIDADA = "validada", "Validada (CUV obtenido)"
    RADICADA = "radicada", "Radicada ante la ARL"
    ANULADA = "anulada", "Anulada"


class FacturaARL(models.Model):
    """
    Factura a la ARL por atención de accidente/enfermedad laboral, con su
    RIPS JSON (Res. 948/2026) y CUV del MUV. ACOPLADA a AccidenteTrabajo:
    no puede existir sin accidente — esa restricción ES la regla 8.

    La llamada real al MUV/Factus requiere credenciales del prestador; se
    integra vía el adaptador stub en rips.py (mismo patrón de Halu Medic),
    reemplazable por el cliente real sin tocar el modelo.
    """

    accidente = models.ForeignKey(
        "accidentes.AccidenteTrabajo", on_delete=models.PROTECT, related_name="facturas_arl"
    )
    atencion = models.ForeignKey(
        "atenciones.Atencion", on_delete=models.PROTECT, null=True, blank=True,
        related_name="facturas_arl",
    )
    numero = models.CharField(max_length=20, blank=True)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=10, choices=EstadoFacturaARL.choices, default=EstadoFacturaARL.BORRADOR)
    rips_json = models.JSONField(default=dict)
    cuv = models.CharField(max_length=96, blank=True, help_text="Código Único de Validación (MUV).")
    cucon = models.CharField(max_length=64, blank=True, help_text="Código Único de Contrato (SIIFA).")
    creada_por = models.ForeignKey("usuarios.Usuario", on_delete=models.PROTECT, related_name="facturas_arl_creadas")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Factura ARL (RIPS)"
        verbose_name_plural = "Facturas ARL (RIPS)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Factura ARL {self.numero or f'borrador #{self.pk}'} — accidente #{self.accidente_id}"

    def clean(self):
        # Blindaje regla 8: la atención facturada debe pertenecer al mismo
        # trabajador del accidente (no facturar a ARL atenciones ordinarias).
        if self.atencion_id and self.accidente_id:
            if self.atencion.trabajador_id != self.accidente.trabajador_id:
                raise ValidationError(
                    "La atención no corresponde al trabajador del accidente: "
                    "solo se factura a la ARL la atención derivada del evento."
                )


class EstadoGlosa(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    ACEPTADA = "aceptada", "Aceptada (IPS acepta)"
    RECHAZADA = "rechazada", "Rechazada (IPS ratifica)"
    SUBSANADA = "subsanada", "Subsanada"
    CONCILIADA = "conciliada", "Conciliada / cerrada"


class Glosa(models.Model):
    """
    Glosa: discrepancia u objeción de una factura por parte de la empresa/ARL.
    La IPS la concilia respondiendo (aceptar, ratificar, subsanar).
    """

    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="glosas", null=True, blank=True)
    factura_arl = models.ForeignKey(FacturaARL, on_delete=models.PROTECT, related_name="glosas", null=True, blank=True)
    codigo = models.CharField(max_length=20, blank=True, default="", help_text="Código de glosa (Res. 3047/2008).")
    descripcion = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(max_length=12, choices=EstadoGlosa.choices, default=EstadoGlosa.PENDIENTE)
    respuesta = models.TextField(blank=True, default="")
    creada_por = models.ForeignKey("usuarios.Usuario", on_delete=models.PROTECT, related_name="glosas_creadas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Glosa"
        verbose_name_plural = "Glosas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Glosa {self.codigo or self.pk} — ${self.valor} [{self.estado}]"
