from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.usuarios.models import Profesional

from .models import (
    CodigoCums,
    CodigoCups,
    ConceptoMedicoOcupacional,
    Diagnostico,
    HistoriaClinicaOcupacional,
    MedicamentoRecetado,
    OrdenMedica,
    Receta,
)


class CodigoCupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodigoCups
        fields = ["id", "codigo", "nombre", "seccion"]


class CodigoCumsSerializer(serializers.ModelSerializer):
    # Etiqueta compuesta para el buscador; `nombre` queda como el genérico puro.
    etiqueta = serializers.SerializerMethodField()

    class Meta:
        model = CodigoCums
        fields = ["id", "codigo", "nombre", "etiqueta", "forma_farmaceutica", "via", "atc"]

    def get_etiqueta(self, obj):
        partes = [obj.nombre, obj.forma_farmaceutica, obj.via]
        return " · ".join(p for p in partes if p)


class DiagnosticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnostico
        fields = [
            "id", "historia", "cie10_codigo", "cie10_desc",
            "cie11_codigo", "cie11_desc", "relacion", "tipo",
            "observacion", "created_at",
        ]

    def validate_historia(self, historia):
        # El médico solo diagnostica sobre historias de sus propias atenciones.
        if historia.atencion.profesional_asignado_id != self.context["request"].user.id:
            raise serializers.ValidationError("La historia no corresponde a una atención asignada a usted.")
        return historia


class HistoriaClinicaSerializer(serializers.ModelSerializer):
    """
    Historia clínica completa — SOLO llega al médico asignado (los permisos
    y el scoping lo garantizan antes de llegar aquí).
    """

    diagnosticos_cie = DiagnosticoSerializer(many=True, read_only=True)

    class Meta:
        model = HistoriaClinicaOcupacional
        fields = [
            "id", "atencion", "profesional",
            "motivo_consulta", "antecedentes", "antecedentes_laborales",
            "revision_sistemas", "examen_fisico", "diagnosticos", "analisis",
            "plan_manejo", "recomendaciones",
            "peso_kg", "talla_cm", "presion_arterial", "frecuencia_cardiaca",
            "frecuencia_respiratoria", "temperatura", "saturacion_o2",
            "diagnosticos_cie", "created_at", "updated_at",
        ]
        read_only_fields = ["profesional"]

    def create(self, validated_data):
        validated_data["profesional"] = self.context["request"].user
        return super().create(validated_data)


class OrdenMedicaSerializer(serializers.ModelSerializer):
    profesional_nombre = serializers.CharField(source="profesional.nombre_completo", read_only=True)

    class Meta:
        model = OrdenMedica
        fields = [
            "id", "atencion", "profesional", "profesional_nombre", "tipo",
            "descripcion", "codigo_cups", "cantidad", "diagnostico_cie10",
            "indicaciones", "estado", "created_at",
        ]
        read_only_fields = ["profesional"]

    def validate_atencion(self, atencion):
        if atencion.profesional_asignado_id != self.context["request"].user.id:
            raise serializers.ValidationError("La atención no está asignada a usted.")
        return atencion

    def create(self, validated_data):
        validated_data["profesional"] = self.context["request"].user
        return super().create(validated_data)


class MedicamentoRecetadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicamentoRecetado
        fields = [
            "id", "medicamento", "concentracion", "forma_farmaceutica",
            "dosis", "via", "frecuencia", "duracion", "cantidad", "indicaciones",
        ]


class RecetaSerializer(serializers.ModelSerializer):
    """Receta con sus medicamentos anidados (creación en un solo POST)."""

    medicamentos = MedicamentoRecetadoSerializer(many=True)
    profesional_nombre = serializers.CharField(source="profesional.nombre_completo", read_only=True)

    class Meta:
        model = Receta
        fields = [
            "id", "atencion", "profesional", "profesional_nombre",
            "diagnostico_cie10", "observaciones", "medicamentos", "created_at",
        ]
        read_only_fields = ["profesional"]

    def validate_medicamentos(self, value):
        if not value:
            raise serializers.ValidationError("La receta debe tener al menos un medicamento.")
        return value

    def validate_atencion(self, atencion):
        if atencion.profesional_asignado_id != self.context["request"].user.id:
            raise serializers.ValidationError("La atención no está asignada a usted.")
        return atencion

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("medicamentos", [])
        validated_data["profesional"] = self.context["request"].user
        receta = Receta.objects.create(**validated_data)
        MedicamentoRecetado.objects.bulk_create(
            [MedicamentoRecetado(receta=receta, **i) for i in items]
        )
        return receta


class ConceptoSerializer(serializers.ModelSerializer):
    """
    Concepto de aptitud. Es el ÚNICO documento visible para empresa_cliente;
    no incluye ningún campo clínico reservado.
    """

    trabajador_nombre = serializers.SerializerMethodField()
    profesional_nombre = serializers.CharField(source="profesional.nombre_completo", read_only=True)

    class Meta:
        model = ConceptoMedicoOcupacional
        fields = [
            "id", "atencion", "historia", "profesional", "profesional_nombre",
            "trabajador_nombre", "licencia_sst", "aptitud", "restricciones",
            "recomendaciones_laborales", "firmado", "fecha_emision",
            "vigencia_hasta", "fecha_recomendacion", "seguimiento_completado", "created_at",
        ]
        read_only_fields = ["profesional", "licencia_sst", "firmado", "fecha_emision"]

    def get_trabajador_nombre(self, obj):
        t = obj.atencion.trabajador
        return t.nombre_completo

    def create(self, validated_data):
        validated_data["profesional"] = self.context["request"].user
        return super().create(validated_data)


class FirmarConceptoSerializer(serializers.Serializer):
    """
    Firma del concepto (regla 5): exige licencia SST vigente y validada del
    profesional que firma. Sin licencia vigente, la firma se rechaza.
    """

    def validate(self, data):
        user = self.context["request"].user
        try:
            profesional = user.profesional
        except Profesional.DoesNotExist:
            raise serializers.ValidationError(
                "El usuario no tiene perfil de profesional registrado."
            )
        licencia = (
            profesional.licencias.filter(
                validada=True, fecha_vencimiento__gte=timezone.now().date()
            )
            .order_by("-fecha_vencimiento")
            .first()
        )
        if licencia is None:
            raise serializers.ValidationError(
                "No es posible firmar: el profesional no tiene una licencia SST "
                "vigente y validada (Res. 4502/2012)."
            )
        data["licencia"] = licencia
        return data
