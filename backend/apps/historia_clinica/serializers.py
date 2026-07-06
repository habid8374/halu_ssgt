from django.utils import timezone
from rest_framework import serializers

from apps.usuarios.models import Profesional

from .models import ConceptoMedicoOcupacional, HistoriaClinicaOcupacional


class HistoriaClinicaSerializer(serializers.ModelSerializer):
    """
    Historia clínica completa — SOLO llega al médico asignado (los permisos
    y el scoping lo garantizan antes de llegar aquí).
    """

    class Meta:
        model = HistoriaClinicaOcupacional
        fields = [
            "id", "atencion", "profesional",
            "motivo_consulta", "antecedentes", "revision_sistemas",
            "examen_fisico", "diagnosticos", "analisis", "plan_manejo",
            "recomendaciones", "created_at", "updated_at",
        ]
        read_only_fields = ["profesional"]

    def create(self, validated_data):
        validated_data["profesional"] = self.context["request"].user
        return super().create(validated_data)


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
