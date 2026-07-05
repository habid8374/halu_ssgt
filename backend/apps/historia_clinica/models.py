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
    revision_sistemas = EncryptedTextField(blank=True)
    examen_fisico = EncryptedTextField(blank=True)
    # Diagnósticos: texto cifrado ahora; codificación CIE-10/CIE-11 estructurada
    # se aborda en fase 4 (interoperabilidad).
    diagnosticos = EncryptedTextField(blank=True)
    analisis = EncryptedTextField(blank=True)
    plan_manejo = EncryptedTextField(blank=True)
    recomendaciones = EncryptedTextField(blank=True)

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
