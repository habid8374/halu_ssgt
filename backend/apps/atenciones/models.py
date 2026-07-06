"""
Núcleo operativo: directorio de empresas/trabajadores, sedes/consultorios y
el ciclo de vida de la Atención con su historial de estados append-only.

Estos modelos alimentan el tablero de flujo en tiempo real (paso 5).
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ConfiguracionIPS(models.Model):
    """
    Datos de la IPS para el MEMBRETE de los documentos (historia, certificado
    de aptitud, órdenes, recetas): razón social, NIT, código de habilitación
    (REPS), dirección/contacto y logo. Singleton por esquema (una IPS por
    tenant). El logo se guarda como data URI (base64) para imprimirse sin
    depender del almacenamiento de medios.
    """

    razon_social = models.CharField(max_length=200, blank=True, default="")
    nit = models.CharField(max_length=25, blank=True, default="")
    codigo_habilitacion = models.CharField(max_length=40, blank=True, default="", help_text="Código de habilitación REPS")
    direccion = models.CharField(max_length=255, blank=True, default="")
    ciudad = models.CharField(max_length=120, blank=True, default="")
    telefono = models.CharField(max_length=60, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    logo_data_uri = models.TextField(blank=True, default="", help_text="Logo en base64 (data URI).")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de la IPS"
        verbose_name_plural = "Configuración de la IPS"

    def __str__(self):
        return self.razon_social or "Configuración de la IPS"


# ---------------------------------------------------------------------------
# Directorio de convenios y ubicaciones
# ---------------------------------------------------------------------------
class ClaseRiesgoARL(models.TextChoices):
    """Clase de riesgo laboral (Decreto 1607/2002)."""

    I = "I", "Clase I — Riesgo mínimo"
    II = "II", "Clase II — Riesgo bajo"
    III = "III", "Clase III — Riesgo medio"
    IV = "IV", "Clase IV — Riesgo alto"
    V = "V", "Clase V — Riesgo máximo"


class Empresa(models.Model):
    """
    Empresa cliente (empleador/aportante). NO es el tenant — el tenant es la IPS.

    Los campos amplían el mínimo para soportar el reporte a la ARL (FURAT) y
    la facturación: NIT + dígito de verificación, actividad económica (CIIU),
    clase de riesgo y ARL de afiliación.
    """

    # --- Identificación ---
    nombre = models.CharField("Razón social", max_length=200)
    nit = models.CharField("NIT", max_length=20)
    digito_verificacion = models.CharField(max_length=1, blank=True, default="")

    # --- Actividad y riesgo (SST / ARL) ---
    actividad_economica_ciiu = models.CharField(
        "Código CIIU", max_length=10, blank=True, default="",
        help_text="Código de actividad económica (CIIU rev. 4 A.C.).",
    )
    actividad_economica_desc = models.CharField(max_length=200, blank=True, default="")
    clase_riesgo = models.CharField(max_length=3, choices=ClaseRiesgoARL.choices, blank=True, default="")
    arl_nombre = models.CharField("ARL", max_length=120, blank=True, default="")

    # --- Ubicación y contacto ---
    departamento = models.CharField(max_length=60, blank=True, default="")
    municipio = models.CharField(max_length=80, blank=True, default="")
    municipio_dane = models.CharField("Código DANE municipio", max_length=5, blank=True, default="")
    direccion = models.CharField(max_length=255, blank=True, default="")
    telefono = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    # --- Responsables ---
    representante_legal = models.CharField(max_length=150, blank=True, default="")
    responsable_sst = models.CharField("Responsable SST", max_length=150, blank=True, default="")
    contacto_sst = models.CharField(max_length=120, blank=True, default="")

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
    """Tipos de documento (tabla oficial RIPS / interoperabilidad)."""

    RC = "RC", "Registro civil"
    TI = "TI", "Tarjeta de identidad"
    CC = "CC", "Cédula de ciudadanía"
    CE = "CE", "Cédula de extranjería"
    PA = "PA", "Pasaporte"
    CN = "CN", "Certificado de nacido vivo"
    AS = "AS", "Adulto sin identificación"
    MS = "MS", "Menor sin identificación"
    PE = "PE", "Permiso especial de permanencia"
    PT = "PT", "Permiso por protección temporal"
    SC = "SC", "Salvoconducto"
    DE = "DE", "Documento extranjero"
    CD = "CD", "Carné diplomático"


class Sexo(models.TextChoices):
    MASCULINO = "M", "Masculino"
    FEMENINO = "F", "Femenino"
    INDETERMINADO = "I", "Indeterminado / Intersexual"


class ZonaTerritorial(models.TextChoices):
    URBANA = "U", "Urbana"
    RURAL = "R", "Rural"


class PertenenciaEtnica(models.TextChoices):
    INDIGENA = "1", "Indígena"
    ROM = "2", "ROM (gitano)"
    RAIZAL = "3", "Raizal (San Andrés y Providencia)"
    PALENQUERO = "4", "Palenquero de San Basilio"
    NEGRO = "5", "Negro(a), mulato(a), afrocolombiano(a)"
    NINGUNA = "6", "Ninguna de las anteriores"


class TipoAfiliacion(models.TextChoices):
    CONTRIBUTIVO = "contributivo", "Contributivo"
    SUBSIDIADO = "subsidiado", "Subsidiado"
    ESPECIAL = "especial", "Régimen especial o de excepción"
    PARTICULAR = "particular", "Particular / No asegurado"


class Trabajador(models.Model):
    """
    Trabajador atendido (paciente). Pertenece a una Empresa (convenio).

    Estructura de datos alineada al conjunto mínimo interoperable
    (Res. 866/2021) y a los campos de usuario del RIPS (Res. 948/2026):
    nombres y apellidos separados, sexo, país/municipio/zona de residencia,
    pertenencia étnica, tipo de afiliación y ocupación (CIUO).

    Retención (regla 2): no se elimina físicamente; se usa `archivado`.
    """

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="trabajadores")

    # --- Identificación (obligatorio) ---
    tipo_documento = models.CharField(max_length=4, choices=TipoDocumento.choices, default=TipoDocumento.CC)
    numero_documento = models.CharField(max_length=30)
    primer_nombre = models.CharField(max_length=60, default="")
    segundo_nombre = models.CharField(max_length=60, blank=True, default="")
    primer_apellido = models.CharField(max_length=60, default="")
    segundo_apellido = models.CharField(max_length=60, blank=True, default="")
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=Sexo.choices, blank=True, default="")

    # --- Residencia (RIPS) ---
    pais_residencia = models.CharField(max_length=3, default="170")  # 170 = Colombia (ISO 3166)
    departamento_residencia = models.CharField(max_length=60, blank=True, default="")
    municipio_residencia = models.CharField(max_length=80, blank=True, default="")
    municipio_dane = models.CharField("Código DANE municipio", max_length=5, blank=True, default="")
    zona_territorial = models.CharField(max_length=1, choices=ZonaTerritorial.choices, blank=True, default="")
    direccion = models.CharField(max_length=255, blank=True, default="")

    # --- Contacto ---
    telefono = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    # --- Caracterización / afiliación ---
    pertenencia_etnica = models.CharField(max_length=1, choices=PertenenciaEtnica.choices, blank=True, default="")
    tipo_afiliacion = models.CharField(max_length=15, choices=TipoAfiliacion.choices, blank=True, default="")
    entidad_responsable_pago = models.CharField("EPS / EAPB", max_length=120, blank=True, default="")

    # --- Ocupacional ---
    cargo = models.CharField(max_length=150, blank=True, default="")
    ocupacion_ciuo = models.CharField("Ocupación (CIUO)", max_length=10, blank=True, default="")

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

    @property
    def nombre_completo(self) -> str:
        partes = [self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido]
        return " ".join(p for p in partes if p)

    def __str__(self):
        return f"{self.nombre_completo} ({self.tipo_documento} {self.numero_documento})"


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


class Profesiograma(models.Model):
    """Matriz de exámenes requeridos por cargo y empresa (Decreto 1072/2015)."""

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="profesiogramas")
    cargo = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Profesiograma"
        verbose_name_plural = "Profesiogramas"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "cargo"], name="uniq_profesiograma_empresa_cargo")
        ]

    def __str__(self):
        return f"{self.empresa.nombre} — {self.cargo}"


class TipoExamenRequerido(models.Model):
    profesiograma = models.ForeignKey(Profesiograma, on_delete=models.CASCADE, related_name="examenes")
    tipo_examen = models.CharField(max_length=20, choices=TipoExamen.choices)
    periodicidad_meses = models.PositiveSmallIntegerField(
        default=12, help_text="Cada cuántos meses se repite (0 = solo una vez)."
    )
    observaciones = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Tipo de examen requerido"
        verbose_name_plural = "Tipos de examen requeridos"

    def __str__(self):
        return f"{self.profesiograma} · {self.tipo_examen} c/{self.periodicidad_meses}m"


# ---------------------------------------------------------------------------
# Batería de pruebas (estaciones del circuito ocupacional)
# ---------------------------------------------------------------------------
class TipoPrueba(models.TextChoices):
    """Estaciones/pruebas del circuito de una IPS ocupacional."""

    MEDICINA = "medicina", "Evaluación médica ocupacional"
    VISIOMETRIA = "visiometria", "Visiometría / Optometría"
    AUDIOMETRIA = "audiometria", "Audiometría"
    ESPIROMETRIA = "espirometria", "Espirometría"
    LABORATORIO = "laboratorio", "Laboratorio clínico"
    PSICOLOGIA = "psicologia", "Evaluación psicológica"
    OTRO = "otro", "Otro paraclínico"


class PruebaRequerida(models.Model):
    """Prueba de la batería exigida por un profesiograma (empresa/cargo)."""

    profesiograma = models.ForeignKey(Profesiograma, on_delete=models.CASCADE, related_name="pruebas")
    tipo_prueba = models.CharField(max_length=15, choices=TipoPrueba.choices)
    detalle = models.CharField(max_length=150, blank=True, default="", help_text="Ej. Cuadro hemático, glicemia.")

    class Meta:
        verbose_name = "Prueba requerida"
        verbose_name_plural = "Pruebas requeridas"

    def __str__(self):
        return f"{self.profesiograma} · {self.get_tipo_prueba_display()}"


class EstadoPrueba(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EN_PROCESO = "en_proceso", "En proceso"
    REALIZADA = "realizada", "Realizada"
    NO_APLICA = "no_aplica", "No aplica"


class PruebaAtencion(models.Model):
    """
    Estación/prueba concreta dentro de una atención (el "circuito"). El
    trabajador pasa por cada prueba pendiente (triaje multi-estación); el
    resultado se puede DIGITAR (resultado estructurado) o ADJUNTAR (archivo),
    o ambos. El concepto de aptitud se habilita cuando el circuito cierra.
    """

    atencion = models.ForeignKey(Atencion, on_delete=models.CASCADE, related_name="pruebas")
    tipo_prueba = models.CharField(max_length=15, choices=TipoPrueba.choices)
    detalle = models.CharField(max_length=150, blank=True, default="")
    estado = models.CharField(max_length=12, choices=EstadoPrueba.choices, default=EstadoPrueba.PENDIENTE, db_index=True)

    # Resultado digitado (estructurado, según el tipo de prueba) y su resumen
    # para el concepto. El adjunto es el soporte escaneado del equipo/lab.
    resultado = models.JSONField(default=dict, blank=True)
    resumen = models.CharField(max_length=255, blank=True, default="")
    archivo = models.FileField(upload_to="pruebas/%Y/%m/", null=True, blank=True)

    realizada_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="pruebas_realizadas"
    )
    realizada_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prueba de atención"
        verbose_name_plural = "Pruebas de atención"
        ordering = ["created_at"]

    @property
    def medico_asignado_id(self):
        return self.atencion.profesional_asignado_id

    def __str__(self):
        return f"{self.get_tipo_prueba_display()} — atención #{self.atencion_id} [{self.estado}]"


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
