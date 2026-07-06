from rest_framework import serializers

from .models import (
    Atencion,
    Cita,
    ConfiguracionIPS,
    Consultorio,
    Empresa,
    HistorialEstado,
    Sede,
    Trabajador,
)


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


class AtencionSerializer(serializers.ModelSerializer):
    """Tarjeta del tablero. Sin datos clínicos: solo identificación y flujo."""

    trabajador_nombre = serializers.SerializerMethodField()
    trabajador_documento = serializers.CharField(source="trabajador.numero_documento", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    consultorio_nombre = serializers.CharField(source="consultorio.nombre", read_only=True, default=None)
    profesional_nombre = serializers.CharField(
        source="profesional_asignado.nombre_completo", read_only=True, default=None
    )

    class Meta:
        model = Atencion
        fields = [
            "id", "trabajador", "trabajador_nombre", "trabajador_documento",
            "empresa", "empresa_nombre",
            "sede", "consultorio", "consultorio_nombre", "tipo_examen", "estado",
            "profesional_asignado", "profesional_nombre",
            "created_at", "estado_actualizado_at",
        ]
        read_only_fields = ["estado", "estado_actualizado_at"]

    def get_trabajador_nombre(self, obj):
        return obj.trabajador.nombre_completo


class CrearAtencionSerializer(serializers.ModelSerializer):
    """Admisión (recepción): crea la atención en estado 'registrado'."""

    class Meta:
        model = Atencion
        fields = ["trabajador", "sede", "consultorio", "tipo_examen", "profesional_asignado"]

    def validate(self, data):
        trabajador = data["trabajador"]
        data["empresa"] = trabajador.empresa
        return data

    def create(self, validated_data):
        validated_data["creado_por"] = self.context["request"].user
        return super().create(validated_data)


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
