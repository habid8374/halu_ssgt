"""
Serializers para la administración de personal de la IPS (rol coordinador).

Crea usuarios autenticables con su rol y, para los roles clínicos, el
`Profesional` asociado y (opcionalmente) su `LicenciaSST`. Todo desde la app:
ningún alta de personal exige el admin de Django (CLAUDE.md §8, «cero comandos»).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import LicenciaSST, Profesional, TipoProfesional, Usuario
from .roles import Rol

# Roles que un coordinador puede dar de alta desde la app. `admin_sistema`
# queda reservado a infraestructura (superusuario/bootstrap), no se crea aquí.
ROLES_GESTIONABLES = {
    Rol.RECEPCION, Rol.MEDICO, Rol.PSICOLOGO_SST, Rol.COORDINADOR, Rol.EMPRESA_CLIENTE,
}
# Roles clínicos que llevan ficha de Profesional (y licencia SST).
ROLES_CLINICOS = {Rol.MEDICO: TipoProfesional.MEDICO, Rol.PSICOLOGO_SST: TipoProfesional.PSICOLOGO}


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Alta y edición de personal. Los datos de profesional/licencia se envían
    planos y solo aplican a roles clínicos (médico / psicólogo SST).
    """

    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=8,
        style={"input_type": "password"},
        help_text="Al crear es obligatoria; al editar, si se envía, reemplaza la actual.",
    )

    # Ficha profesional (solo roles clínicos).
    registro_profesional = serializers.CharField(required=False, allow_blank=True)
    especialidad = serializers.CharField(required=False, allow_blank=True)

    # Licencia SST (opcional; el coordinador la valida en fase 1).
    licencia_numero = serializers.CharField(required=False, allow_blank=True, write_only=True)
    licencia_entidad = serializers.CharField(required=False, allow_blank=True, write_only=True)
    licencia_expedicion = serializers.DateField(required=False, allow_null=True, write_only=True)
    licencia_vencimiento = serializers.DateField(required=False, allow_null=True, write_only=True)

    # Lectura para la UI.
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    sede_nombre = serializers.CharField(source="sede.nombre", read_only=True, default=None)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True, default=None)
    tiene_licencia_vigente = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id", "email", "nombre_completo", "rol", "rol_display",
            "sede", "sede_nombre", "empresa", "empresa_nombre",
            "is_active", "password",
            "registro_profesional", "especialidad", "tiene_licencia_vigente",
            "licencia_numero", "licencia_entidad", "licencia_expedicion", "licencia_vencimiento",
        ]

    # ---- lectura -------------------------------------------------------
    def get_tiene_licencia_vigente(self, obj):
        prof = getattr(obj, "profesional", None)
        return bool(prof and prof.tiene_licencia_vigente)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        prof = getattr(instance, "profesional", None)
        data["registro_profesional"] = prof.registro_profesional if prof else ""
        data["especialidad"] = prof.especialidad if prof else ""
        return data

    # ---- validación ----------------------------------------------------
    def _extraer_extras(self, validated):
        return {
            "password": validated.pop("password", ""),
            "registro_profesional": validated.pop("registro_profesional", ""),
            "especialidad": validated.pop("especialidad", ""),
            "licencia_numero": validated.pop("licencia_numero", ""),
            "licencia_entidad": validated.pop("licencia_entidad", ""),
            "licencia_expedicion": validated.pop("licencia_expedicion", None),
            "licencia_vencimiento": validated.pop("licencia_vencimiento", None),
        }

    def validate_rol(self, value):
        if value not in ROLES_GESTIONABLES:
            raise serializers.ValidationError("Rol no administrable desde la app.")
        return value

    def validate(self, data):
        rol = data.get("rol", getattr(self.instance, "rol", None))
        sede = data.get("sede", getattr(self.instance, "sede", None))
        empresa = data.get("empresa", getattr(self.instance, "empresa", None))
        if rol in {Rol.RECEPCION, Rol.MEDICO, Rol.PSICOLOGO_SST} and sede is None:
            raise serializers.ValidationError({"sede": "Este rol requiere una sede."})
        if rol == Rol.EMPRESA_CLIENTE and empresa is None:
            raise serializers.ValidationError({"empresa": "El portal de empresa requiere una empresa asociada."})
        if self.instance is None and not data.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria al crear el usuario."})
        # Coherencia de scope: solo empresa_cliente lleva empresa; esta no lleva
        # sede. El coordinador es transversal (sede opcional).
        if rol != Rol.EMPRESA_CLIENTE:
            data["empresa"] = None
        else:
            data["sede"] = None
        return data

    # ---- escritura -----------------------------------------------------
    def _sync_profesional(self, usuario, extras):
        """Crea/actualiza la ficha de profesional y su licencia si aplica."""
        tipo = ROLES_CLINICOS.get(usuario.rol)
        if tipo is None:
            return
        prof, _ = Profesional.objects.get_or_create(usuario=usuario, defaults={"tipo": tipo})
        prof.tipo = tipo
        prof.registro_profesional = extras["registro_profesional"]
        prof.especialidad = extras["especialidad"]
        prof.save()
        if extras["licencia_numero"] and extras["licencia_expedicion"] and extras["licencia_vencimiento"]:
            LicenciaSST.objects.update_or_create(
                profesional=prof, numero=extras["licencia_numero"],
                defaults={
                    "entidad_expide": extras["licencia_entidad"],
                    "fecha_expedicion": extras["licencia_expedicion"],
                    "fecha_vencimiento": extras["licencia_vencimiento"],
                    "validada": True,
                    "validada_at": timezone.now(),
                },
            )

    @transaction.atomic
    def create(self, validated_data):
        extras = self._extraer_extras(validated_data)
        password = extras["password"]
        try:
            usuario = Usuario.objects.create_user(password=password, **validated_data)
        except Exception as e:  # email duplicado, etc.
            raise serializers.ValidationError({"email": str(e)})
        try:
            usuario.full_clean(exclude=["password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        self._sync_profesional(usuario, extras)
        return usuario

    @transaction.atomic
    def update(self, instance, validated_data):
        extras = self._extraer_extras(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if extras["password"]:
            instance.set_password(extras["password"])
        instance.save()
        self._sync_profesional(instance, extras)
        return instance
