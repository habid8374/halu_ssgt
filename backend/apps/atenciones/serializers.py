from rest_framework import serializers

from .models import (
    Atencion,
    AutorizacionServicio,
    Cita,
    ConfiguracionIPS,
    Consultorio,
    Empresa,
    HistorialEstado,
    Profesiograma,
    PruebaAtencion,
    PruebaRequerida,
    Sede,
    TipoExamenRequerido,
    Trabajador,
)


class AutorizacionServicioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = AutorizacionServicio
        fields = [
            "id", "empresa", "empresa_nombre", "trabajador_documento", "trabajador_nombre",
            "tipo_examen", "cargo", "numero", "vigencia_hasta", "estado", "created_at",
        ]
        read_only_fields = ["estado"]


class ConfiguracionIPSSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionIPS
        fields = [
            "razon_social", "nit", "codigo_habilitacion",
            "direccion", "ciudad", "telefono", "email", "logo_data_uri",
        ]

    def validate_logo_data_uri(self, v):
        if v and not v.startswith("data:image/"):
            raise serializers.ValidationError("El logo debe ser una imagen (data URI).")
        # Límite ~600 KB en base64 para no inflar la base de datos.
        if v and len(v) > 800_000:
            raise serializers.ValidationError("El logo es demasiado grande (use una imagen más liviana).")
        return v


class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = ["id", "nombre", "codigo", "direccion", "activa"]


class ConsultorioSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source="sede.nombre", read_only=True)

    class Meta:
        model = Consultorio
        fields = ["id", "sede", "sede_nombre", "nombre", "activo"]


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id", "nombre", "nit", "digito_verificacion",
            "actividad_economica_ciiu", "actividad_economica_desc",
            "clase_riesgo", "arl_nombre",
            "departamento", "municipio", "municipio_dane",
            "direccion", "telefono", "email",
            "representante_legal", "responsable_sst", "contacto_sst",
            "activo",
        ]


class TrabajadorSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    # Aunque el modelo tenga default="" (para migración limpia), estos son
    # obligatorios al registrar desde la app.
    primer_nombre = serializers.CharField(required=True, allow_blank=False, max_length=60)
    primer_apellido = serializers.CharField(required=True, allow_blank=False, max_length=60)
    fecha_nacimiento = serializers.DateField(required=True)
    sexo = serializers.ChoiceField(
        choices=[c[0] for c in Trabajador._meta.get_field("sexo").choices], required=True
    )

    class Meta:
        model = Trabajador
        fields = [
            "id", "empresa", "empresa_nombre", "nombre_completo",
            "tipo_documento", "numero_documento",
            "primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido",
            "fecha_nacimiento", "sexo",
            "pais_residencia", "departamento_residencia", "municipio_residencia",
            "municipio_dane", "zona_territorial", "direccion",
            "telefono", "email",
            "pertenencia_etnica", "tipo_afiliacion", "entidad_responsable_pago",
            "cargo", "ocupacion_ciuo",
        ]


class PruebaRequeridaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PruebaRequerida
        fields = ["id", "tipo_prueba", "detalle"]


class TipoExamenRequeridoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoExamenRequerido
        fields = ["id", "tipo_examen", "periodicidad_meses", "observaciones"]


class ProfesiogramaSerializer(serializers.ModelSerializer):
    """Profesiograma con su batería de pruebas y exámenes (anidados)."""

    pruebas = PruebaRequeridaSerializer(many=True, required=False)
    examenes = TipoExamenRequeridoSerializer(many=True, required=False)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Profesiograma
        fields = ["id", "empresa", "empresa_nombre", "cargo", "activo", "pruebas", "examenes"]

    def _guardar_hijos(self, prof, pruebas, examenes):
        if pruebas is not None:
            prof.pruebas.all().delete()
            PruebaRequerida.objects.bulk_create(
                [PruebaRequerida(profesiograma=prof, **p) for p in pruebas]
            )
        if examenes is not None:
            prof.examenes.all().delete()
            TipoExamenRequerido.objects.bulk_create(
                [TipoExamenRequerido(profesiograma=prof, **e) for e in examenes]
            )

    def create(self, validated_data):
        pruebas = validated_data.pop("pruebas", None)
        examenes = validated_data.pop("examenes", None)
        prof = Profesiograma.objects.create(**validated_data)
        self._guardar_hijos(prof, pruebas, examenes)
        return prof

    def update(self, instance, validated_data):
        pruebas = validated_data.pop("pruebas", None)
        examenes = validated_data.pop("examenes", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        self._guardar_hijos(instance, pruebas, examenes)
        return instance


class PruebaAtencionSerializer(serializers.ModelSerializer):
    """Estación/prueba del circuito. Incluye resultado digitado y/o adjunto."""

    archivo_url = serializers.SerializerMethodField()
    tipo_prueba_label = serializers.CharField(source="get_tipo_prueba_display", read_only=True)
    trabajador_nombre = serializers.SerializerMethodField()
    trabajador_documento = serializers.CharField(source="atencion.trabajador.numero_documento", read_only=True)
    empresa_nombre = serializers.CharField(source="atencion.empresa.nombre", read_only=True)

    class Meta:
        model = PruebaAtencion
        fields = [
            "id", "atencion", "tipo_prueba", "tipo_prueba_label", "detalle",
            "estado", "resultado", "resumen", "archivo", "archivo_url",
            "trabajador_nombre", "trabajador_documento", "empresa_nombre",
            "realizada_por", "realizada_at", "created_at",
        ]
        read_only_fields = ["realizada_por", "realizada_at", "archivo_url"]

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None

    def get_trabajador_nombre(self, obj):
        return obj.atencion.trabajador.nombre_completo


class AtencionSerializer(serializers.ModelSerializer):
    """Tarjeta del tablero. Sin datos clínicos: solo identificación y flujo."""

    trabajador_nombre = serializers.SerializerMethodField()
    trabajador_documento = serializers.CharField(source="trabajador.numero_documento", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    consultorio_nombre = serializers.CharField(source="consultorio.nombre", read_only=True, default=None)
    profesional_nombre = serializers.CharField(
        source="profesional_asignado.nombre_completo", read_only=True, default=None
    )

    pruebas_resumen = serializers.SerializerMethodField()

    class Meta:
        model = Atencion
        fields = [
            "id", "trabajador", "trabajador_nombre", "trabajador_documento",
            "empresa", "empresa_nombre",
            "sede", "consultorio", "consultorio_nombre", "tipo_examen", "estado",
            "profesional_asignado", "profesional_nombre", "pruebas_resumen",
            "created_at", "estado_actualizado_at",
        ]
        read_only_fields = ["estado", "estado_actualizado_at"]

    def get_trabajador_nombre(self, obj):
        return obj.trabajador.nombre_completo

    def get_pruebas_resumen(self, obj):
        pruebas = obj.pruebas.all() if hasattr(obj, "pruebas") else []
        total = len(pruebas)
        if not total:
            return None
        realizadas = sum(1 for p in pruebas if p.estado in ("realizada", "no_aplica"))
        return {"total": total, "realizadas": realizadas, "completo": realizadas == total}


class CrearAtencionSerializer(serializers.ModelSerializer):
    """
    Admisión (recepción): crea la atención en estado 'registrado' y arma el
    CIRCUITO de pruebas a partir del profesiograma (empresa + cargo). Si no hay
    profesiograma, deja al menos la evaluación médica.
    """

    pruebas = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True,
        help_text="Tipos de prueba a incluir; si se omite, se toma del profesiograma.",
    )

    class Meta:
        model = Atencion
        fields = ["trabajador", "sede", "consultorio", "tipo_examen", "profesional_asignado", "pruebas"]

    def validate(self, data):
        trabajador = data["trabajador"]
        data["empresa"] = trabajador.empresa
        return data

    def create(self, validated_data):
        from .models import PruebaAtencion, Profesiograma, TipoPrueba

        pruebas_pedidas = validated_data.pop("pruebas", None)
        validated_data["creado_por"] = self.context["request"].user
        atencion = super().create(validated_data)

        tipos = list(pruebas_pedidas) if pruebas_pedidas else []
        if not tipos:
            prof = (
                Profesiograma.objects.filter(
                    empresa=atencion.empresa, cargo__iexact=(atencion.trabajador.cargo or ""), activo=True
                ).prefetch_related("pruebas").first()
            )
            if prof:
                tipos = [pr.tipo_prueba for pr in prof.pruebas.all()]
        # Siempre incluir la evaluación médica como estación base.
        if TipoPrueba.MEDICINA not in tipos:
            tipos = [TipoPrueba.MEDICINA] + tipos
        vistos = []
        for t in tipos:
            if t in vistos:
                continue
            vistos.append(t)
            PruebaAtencion.objects.create(atencion=atencion, tipo_prueba=t)
        return atencion


class ProfesiogramaResolverSerializer(serializers.Serializer):
    """Previsualización de la batería por empresa + cargo (para admisión)."""

    empresa = serializers.IntegerField()
    cargo = serializers.CharField(allow_blank=True)


class TransicionSerializer(serializers.Serializer):
    """Payload de POST /atenciones/{id}/transicion/."""

    estado = serializers.ChoiceField(choices=[c[0] for c in Atencion._meta.get_field("estado").choices])
    nota = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CitaSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.SerializerMethodField()
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    profesional_nombre = serializers.CharField(
        source="profesional_asignado.nombre_completo", read_only=True, default=None
    )

    class Meta:
        model = Cita
        fields = [
            "id", "trabajador", "trabajador_nombre", "empresa", "empresa_nombre",
            "sede", "profesional_asignado", "profesional_nombre", "tipo_examen",
            "fecha_hora", "estado", "nota", "atencion", "created_at",
        ]
        read_only_fields = ["empresa", "estado", "atencion"]

    def get_trabajador_nombre(self, obj):
        return obj.trabajador.nombre_completo

    def validate(self, data):
        if "trabajador" in data:
            data["empresa"] = data["trabajador"].empresa
        return data

    def create(self, validated_data):
        validated_data["creado_por"] = self.context["request"].user
        return super().create(validated_data)


class HistorialEstadoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.nombre_completo", read_only=True)

    class Meta:
        model = HistorialEstado
        fields = ["id", "estado_anterior", "estado_nuevo", "usuario", "usuario_nombre", "nota", "timestamp"]
