from rest_framework import serializers

from .models import (
    Atencion,
    Cita,
    Consultorio,
    Empresa,
    HistorialEstado,
    Sede,
    Trabajador,
)


class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = ["id", "nombre", "codigo", "activa"]


class ConsultorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultorio
        fields = ["id", "sede", "nombre", "activo"]


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ["id", "nombre", "nit", "direccion", "telefono", "email", "activo"]


class TrabajadorSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Trabajador
        fields = [
            "id", "empresa", "empresa_nombre", "tipo_documento", "numero_documento",
            "nombres", "apellidos", "cargo", "telefono", "email",
        ]


class AtencionSerializer(serializers.ModelSerializer):
    """Tarjeta del tablero. Sin datos clínicos: solo identificación y flujo."""

    trabajador_nombre = serializers.SerializerMethodField()
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    consultorio_nombre = serializers.CharField(source="consultorio.nombre", read_only=True, default=None)
    profesional_nombre = serializers.CharField(
        source="profesional_asignado.nombre_completo", read_only=True, default=None
    )

    class Meta:
        model = Atencion
        fields = [
            "id", "trabajador", "trabajador_nombre", "empresa", "empresa_nombre",
            "sede", "consultorio", "consultorio_nombre", "tipo_examen", "estado",
            "profesional_asignado", "profesional_nombre",
            "created_at", "estado_actualizado_at",
        ]
        read_only_fields = ["estado", "estado_actualizado_at"]

    def get_trabajador_nombre(self, obj):
        return f"{obj.trabajador.nombres} {obj.trabajador.apellidos}"


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
        return f"{obj.trabajador.nombres} {obj.trabajador.apellidos}"

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
