"""
Historia clínica ocupacional (reservada, cifrada) y sus documentos derivados.

Separación estricta por diseño (CLAUDE.md regla 1):
  - HistoriaClinicaOcupacional: campos clínicos cifrados. NUNCA accesible por
    el rol empresa_cliente. Acceso solo del médico asignado.
  - ConceptoMedicoOcupacional: salida filtrada (aptitud + restricciones) que
    SÍ ve el empleador. No contiene campos clínicos reservados.

La batería psicosocial (InstrumentoPsicosocial) es fase 2 — no se implementa
aquí (custodia separada del resto de la historia).
"""
from django.db import models
from django.utils import timezone

from .fields import EncryptedCharField, EncryptedTextField


class HistoriaClinicaOcupacional(models.Model):
    """
    Documento clínico privado y reservado (Res. 1995/1999, Res. 1843/2025).

    Retención mínima 15 años (regla 2): no se borra físicamente; `archivada`.
    Campos clínicos cifrados a nivel de columna (regla 10).
    """

    atencion = models.OneToOneField(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="historia_clinica"
    )
    profesional = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="historias_clinicas",
        limit_choices_to={"rol": "medico"},
    )

    # --- Contenido clínico reservado (cifrado) ---
    motivo_consulta = EncryptedTextField(blank=True)
    antecedentes = EncryptedTextField(blank=True)
    # Antecedentes laborales (ocupacionales): clave en salud ocupacional.
    antecedentes_laborales = EncryptedTextField(blank=True)
    revision_sistemas = EncryptedTextField(blank=True)
    examen_fisico = EncryptedTextField(blank=True)
    # Diagnósticos: además del texto libre (cifrado), la codificación CIE-10/
    # CIE-11 estructurada vive en el modelo `Diagnostico` (selección de
    # catálogo), soporte del RIPS/RDA y del concepto.
    diagnosticos = EncryptedTextField(blank=True)
    analisis = EncryptedTextField(blank=True)
    plan_manejo = EncryptedTextField(blank=True)
    recomendaciones = EncryptedTextField(blank=True)

    # --- Signos vitales / antropometría (reservados por acceso, no cifrados
    # para permitir impresión y cálculos; solo el médico asignado los ve) ---
    peso_kg = models.CharField(max_length=8, blank=True, default="")
    talla_cm = models.CharField(max_length=8, blank=True, default="")
    presion_arterial = models.CharField(max_length=12, blank=True, default="", help_text="Ej. 120/80")
    frecuencia_cardiaca = models.CharField(max_length=6, blank=True, default="")
    frecuencia_respiratoria = models.CharField(max_length=6, blank=True, default="")
    temperatura = models.CharField(max_length=6, blank=True, default="")
    saturacion_o2 = models.CharField(max_length=6, blank=True, default="")

    archivada = models.BooleanField(default=False)  # archivado en frío, no borrado
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Historia clínica ocupacional"
        verbose_name_plural = "Historias clínicas ocupacionales"

    def __str__(self):
        # Nunca exponer contenido clínico en __str__/logs (regla §7).
        return f"HC ocupacional de atención #{self.atencion_id}"


class Aptitud(models.TextChoices):
    APTO = "apto", "Apto"
    APTO_CON_RESTRICCIONES = "apto_restricciones", "Apto con restricciones/recomendaciones"
    NO_APTO = "no_apto", "No apto"
    APLAZADO = "aplazado", "Aplazado"


class ConceptoMedicoOcupacional(models.Model):
    """
    Concepto de aptitud (Res. 1843/2025 art. 19): ÚNICO documento que ve el
    empleador. Se genera a partir de la historia clínica pero con campos
    filtrados — aquí NO hay campos clínicos reservados ni cifrado.

    Regla 5: al firmar debe usarse una LicenciaSST vigente del profesional;
    esa validación se aplica al emitir (serializer/servicio), y se referencia
    la licencia usada.
    """

    atencion = models.OneToOneField(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="concepto"
    )
    historia = models.OneToOneField(
        HistoriaClinicaOcupacional, on_delete=models.PROTECT, related_name="concepto"
    )
    profesional = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="conceptos_emitidos"
    )
    # Licencia SST usada para firmar (regla 5).
    licencia_sst = models.ForeignKey(
        "usuarios.LicenciaSST", on_delete=models.PROTECT, related_name="conceptos", null=True
    )

    aptitud = models.CharField(max_length=25, choices=Aptitud.choices)
    # Restricciones / recomendaciones laborales: SÍ visibles al empleador.
    restricciones = models.TextField(blank=True)
    recomendaciones_laborales = models.TextField(blank=True)

    firmado = models.BooleanField(default=False)
    fecha_emision = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    # Fecha de la recomendación: base del plazo de 20 días hábiles (regla 7).
    fecha_recomendacion = models.DateField(null=True, blank=True)
    # Seguimiento de la adaptación de condiciones: al marcarse, la alerta
    # de 20 días hábiles se cierra (apps.accidentes.tasks).
    seguimiento_completado = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Concepto médico ocupacional"
        verbose_name_plural = "Conceptos médicos ocupacionales"

    def __str__(self):
        return f"Concepto {self.aptitud} — atención #{self.atencion_id}"


class TipoConsentimiento(models.TextChoices):
    GENERAL = "general", "Atención general"
    PARACLINICOS = "paraclinicos", "Pruebas complementarias / paraclínicos"


class ConsentimientoInformado(models.Model):
    """
    Consentimiento informado con trazabilidad (Ley 23/1981, Ley 1581/2012).

    Regla 3: obligatorio antes de pruebas complementarias. Se guarda la versión
    del documento firmado, timestamp e IP/dispositivo.
    """

    atencion = models.ForeignKey(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="consentimientos"
    )
    trabajador = models.ForeignKey(
        "atenciones.Trabajador", on_delete=models.PROTECT, related_name="consentimientos"
    )
    tipo = models.CharField(max_length=15, choices=TipoConsentimiento.choices, default=TipoConsentimiento.GENERAL)

    version_documento = models.CharField(max_length=30, help_text="Versión del texto de consentimiento firmado.")
    documento_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 del texto firmado.")
    firmado_at = models.DateTimeField(default=timezone.now)
    ip = models.GenericIPAddressField(null=True, blank=True)
    dispositivo = models.CharField(max_length=255, blank=True)
    firma = models.FileField(upload_to="consentimientos/", null=True, blank=True)

    class Meta:
        verbose_name = "Consentimiento informado"
        verbose_name_plural = "Consentimientos informados"

    def __str__(self):
        return f"Consentimiento {self.tipo} v{self.version_documento} — atención #{self.atencion_id}"


class TipoInstrumento(models.TextChoices):
    INTRALABORAL = "intralaboral", "Cuestionario intralaboral"
    EXTRALABORAL = "extralaboral", "Cuestionario extralaboral"
    ESTRES = "estres", "Cuestionario de estrés"
    FICHA = "ficha", "Ficha de datos sociodemográficos"


class NivelRiesgo(models.TextChoices):
    SIN_RIESGO = "sin_riesgo", "Sin riesgo / despreciable"
    BAJO = "bajo", "Bajo"
    MEDIO = "medio", "Medio"
    ALTO = "alto", "Alto"
    MUY_ALTO = "muy_alto", "Muy alto"


class InstrumentoPsicosocial(models.Model):
    """
    Instrumento de la batería de riesgo psicosocial (Res. 2404/2019).

    CUSTODIA SEPARADA (regla 4): el instrumento individual SOLO lo ve el
    psicólogo que lo aplicó. Empleador y coordinador acceden únicamente a
    informes consolidados agregados (endpoint /psicosocial/consolidado/).
    El contenido de respuestas va cifrado (regla 10).
    """

    trabajador = models.ForeignKey(
        "atenciones.Trabajador", on_delete=models.PROTECT, related_name="instrumentos_psicosociales"
    )
    atencion = models.ForeignKey(
        "atenciones.Atencion", on_delete=models.PROTECT, null=True, blank=True,
        related_name="instrumentos_psicosociales",
    )
    tipo = models.CharField(max_length=15, choices=TipoInstrumento.choices)
    aplicado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT,
        related_name="instrumentos_aplicados", limit_choices_to={"rol": "psicologo_sst"},
    )
    fecha_aplicacion = models.DateField(default=timezone.localdate)
    nivel_riesgo = models.CharField(max_length=10, choices=NivelRiesgo.choices)
    # Respuestas/observaciones individuales: cifradas, nunca agregables por API.
    contenido = EncryptedTextField(blank=True)
    archivado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Instrumento psicosocial"
        verbose_name_plural = "Instrumentos psicosociales"

    def __str__(self):
        # Sin datos del contenido en __str__ (custodia).
        return f"{self.get_tipo_display()} — trabajador #{self.trabajador_id} ({self.fecha_aplicacion})"


class TipoDocumentoAdjunto(models.TextChoices):
    PARACLINICO = "paraclinico", "Resultado de paraclínico"
    LABORATORIO = "laboratorio", "Laboratorio"
    IMAGEN = "imagen", "Imagen diagnóstica"
    OTRO = "otro", "Otro"


class DocumentoAdjunto(models.Model):
    """
    Documento adjunto (paraclínicos, PDFs). Almacenamiento abstraído vía
    django-storages: FileSystemStorage en dev, S3-compatible por configuración
    (STORAGE_BACKEND). Cifrado en reposo a nivel de bucket cuando es S3.
    """

    atencion = models.ForeignKey(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="adjuntos"
    )
    tipo = models.CharField(max_length=15, choices=TipoDocumentoAdjunto.choices, default=TipoDocumentoAdjunto.OTRO)
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to="adjuntos/%Y/%m/")
    archivo_hash = models.CharField(max_length=64, blank=True)
    subido_por = models.ForeignKey("usuarios.Usuario", on_delete=models.PROTECT, related_name="adjuntos_subidos")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento adjunto"
        verbose_name_plural = "Documentos adjuntos"

    def __str__(self):
        return f"{self.nombre} ({self.tipo}) — atención #{self.atencion_id}"


# ---------------------------------------------------------------------------
# Diagnósticos codificados (CIE-10 / CIE-11) — módulo del médico
# ---------------------------------------------------------------------------
class TipoDiagnostico(models.TextChoices):
    """`tipoDiagnosticoPrincipal` del RIPS (Res. 2275/2023)."""

    IMPRESION = "01", "Impresión diagnóstica"
    CONFIRMADO_NUEVO = "02", "Confirmado nuevo"
    CONFIRMADO_REPETIDO = "03", "Confirmado repetido"


class RelacionDiagnostico(models.TextChoices):
    PRINCIPAL = "principal", "Principal"
    RELACIONADO = "relacionado", "Relacionado"


class Diagnostico(models.Model):
    """
    Diagnóstico codificado de una historia clínica. Se elige de catálogo
    (CIE-10, y CIE-11 durante la transición Res. 1442/2024). Sostiene el
    RIPS/RDA y el concepto de aptitud. Reservado: solo el médico asignado.
    """

    historia = models.ForeignKey(
        HistoriaClinicaOcupacional, on_delete=models.PROTECT, related_name="diagnosticos_cie"
    )
    cie10_codigo = models.CharField(max_length=6)
    cie10_desc = models.CharField(max_length=255)
    # CIE-11 (transición): opcional mientras se consolida la equivalencia.
    cie11_codigo = models.CharField(max_length=12, blank=True, default="")
    cie11_desc = models.CharField(max_length=255, blank=True, default="")
    relacion = models.CharField(
        max_length=12, choices=RelacionDiagnostico.choices,
        default=RelacionDiagnostico.PRINCIPAL,
    )
    tipo = models.CharField(
        max_length=2, choices=TipoDiagnostico.choices, default=TipoDiagnostico.IMPRESION
    )
    observacion = EncryptedTextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Diagnóstico"
        verbose_name_plural = "Diagnósticos"
        # "principal" < "relacionado" alfabéticamente → principal primero.
        ordering = ["relacion", "created_at"]

    @property
    def medico_asignado_id(self):
        return self.historia.atencion.profesional_asignado_id

    def __str__(self):
        return f"{self.cie10_codigo} ({self.relacion}) — HC #{self.historia_id}"


# ---------------------------------------------------------------------------
# Órdenes médicas: paraclínicos, procedimientos, remisiones, incapacidad
# ---------------------------------------------------------------------------
class TipoOrden(models.TextChoices):
    LABORATORIO = "laboratorio", "Laboratorio clínico"
    IMAGEN = "imagen", "Imagen diagnóstica"
    PARACLINICO = "paraclinico", "Otro paraclínico"
    PROCEDIMIENTO = "procedimiento", "Procedimiento"
    INTERCONSULTA = "interconsulta", "Interconsulta / remisión"
    INCAPACIDAD = "incapacidad", "Incapacidad médica"
    OTRO = "otro", "Otra orden"


class EstadoOrden(models.TextChoices):
    SOLICITADA = "solicitada", "Solicitada"
    REALIZADA = "realizada", "Realizada"
    ANULADA = "anulada", "Anulada"


class OrdenMedica(models.Model):
    """
    Orden médica emitida por el médico tratante (paraclínicos, procedimientos,
    remisiones, incapacidad). Se imprime/entrega al trabajador. Solo el médico
    asignado a la atención la crea y consulta.
    """

    atencion = models.ForeignKey(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="ordenes"
    )
    profesional = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="ordenes_emitidas"
    )
    tipo = models.CharField(max_length=15, choices=TipoOrden.choices, default=TipoOrden.LABORATORIO)
    descripcion = models.CharField(max_length=255, help_text="Estudio, procedimiento o servicio solicitado.")
    codigo_cups = models.CharField(max_length=12, blank=True, default="", help_text="Código CUPS (opcional).")
    cantidad = models.PositiveSmallIntegerField(default=1)
    diagnostico_cie10 = models.CharField(max_length=6, blank=True, default="")
    indicaciones = models.TextField(blank=True, default="")
    estado = models.CharField(max_length=12, choices=EstadoOrden.choices, default=EstadoOrden.SOLICITADA)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Orden médica"
        verbose_name_plural = "Órdenes médicas"
        ordering = ["-created_at"]

    @property
    def medico_asignado_id(self):
        return self.atencion.profesional_asignado_id

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.descripcion} — atención #{self.atencion_id}"


# ---------------------------------------------------------------------------
# Recetas / fórmulas médicas
# ---------------------------------------------------------------------------
class Receta(models.Model):
    """
    Fórmula médica (receta). Encabezado + medicamentos. La crea el médico
    asignado y se imprime/entrega al trabajador.
    """

    atencion = models.ForeignKey(
        "atenciones.Atencion", on_delete=models.PROTECT, related_name="recetas"
    )
    profesional = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="recetas_emitidas"
    )
    diagnostico_cie10 = models.CharField(max_length=6, blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Receta"
        verbose_name_plural = "Recetas"
        ordering = ["-created_at"]

    @property
    def medico_asignado_id(self):
        return self.atencion.profesional_asignado_id

    def __str__(self):
        return f"Receta #{self.pk} — atención #{self.atencion_id}"


class MedicamentoRecetado(models.Model):
    """Renglón de medicamento de una receta."""

    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name="medicamentos")
    medicamento = models.CharField(max_length=200)
    concentracion = models.CharField(max_length=60, blank=True, default="", help_text="Ej. 500 mg")
    forma_farmaceutica = models.CharField(max_length=60, blank=True, default="", help_text="Ej. tableta, jarabe")
    dosis = models.CharField(max_length=120, blank=True, default="", help_text="Ej. 1 tableta")
    via = models.CharField(max_length=40, blank=True, default="", help_text="Ej. oral")
    frecuencia = models.CharField(max_length=60, blank=True, default="", help_text="Ej. cada 8 horas")
    duracion = models.CharField(max_length=60, blank=True, default="", help_text="Ej. 7 días")
    cantidad = models.CharField(max_length=40, blank=True, default="", help_text="Ej. 21 tabletas")
    indicaciones = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Medicamento recetado"
        verbose_name_plural = "Medicamentos recetados"

    @property
    def medico_asignado_id(self):
        return self.receta.atencion.profesional_asignado_id

    def __str__(self):
        return f"{self.medicamento} — receta #{self.receta_id}"
