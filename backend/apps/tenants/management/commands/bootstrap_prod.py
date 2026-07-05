"""
Arranque de PRODUCCIÓN (idempotente, sin datos demo).

Lee variables de entorno y deja el sistema operable:
  1. Tenant público (routing).
  2. IPS principal + su dominio (el de Railway mientras no hay dominio
     propio; cuando exista, se agregan más dominios/IPS desde el admin).
  3. Superusuario de plataforma en el esquema público Y en la IPS principal
     (mismo correo/clave), con rol admin_sistema: entra al /admin del
     dominio, crea usuarios con sus roles, sedes, empresas y tarifas.
  4. Sede inicial de la IPS.

Variables:
  DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD  (obligatorias)
  BOOTSTRAP_DOMINIO       dominio del backend (ej: halu.up.railway.app)
  BOOTSTRAP_IPS_NOMBRE    nombre de la IPS principal (default: IPS Principal)
  BOOTSTRAP_IPS_NIT       NIT (default: 000000000-0)
  BOOTSTRAP_IPS_SCHEMA    esquema (default: principal)
  BOOTSTRAP_SEDE          nombre de la sede inicial (default: Sede Principal)
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import IPS, Dominio


class Command(BaseCommand):
    help = "Bootstrap de producción: IPS principal, dominio, superusuario y sede."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        dominio = os.environ.get("BOOTSTRAP_DOMINIO")
        if not (email and password and dominio):
            raise CommandError(
                "Faltan variables: DJANGO_SUPERUSER_EMAIL, "
                "DJANGO_SUPERUSER_PASSWORD y BOOTSTRAP_DOMINIO son obligatorias."
            )
        nombre = os.environ.get("BOOTSTRAP_IPS_NOMBRE", "IPS Principal")
        nit = os.environ.get("BOOTSTRAP_IPS_NIT", "000000000-0")
        schema = os.environ.get("BOOTSTRAP_IPS_SCHEMA", "principal")
        sede_nombre = os.environ.get("BOOTSTRAP_SEDE", "Sede Principal")

        # 1-2. Tenants y dominio del backend.
        IPS.objects.get_or_create(
            schema_name=get_public_schema_name(),
            defaults={"nombre": "Plataforma Halu", "nit": "999999999-9"},
        )
        ips, creada = IPS.objects.get_or_create(
            schema_name=schema, defaults={"nombre": nombre, "nit": nit}
        )
        Dominio.objects.get_or_create(
            domain=dominio, defaults={"tenant": ips, "is_primary": True}
        )
        self.stdout.write(self.style.SUCCESS(
            f"IPS '{ips.nombre}' ({schema}) {'creada' if creada else 'ya existía'} "
            f"con dominio {dominio}."
        ))

        # 3. Superusuario (idempotente) en public y en la IPS principal.
        def asegurar_superusuario(nombre_schema):
            with schema_context(nombre_schema):
                from apps.usuarios.models import Usuario

                if not Usuario.objects.filter(email=email).exists():
                    Usuario.objects.create_superuser(
                        email=email, password=password,
                        nombre_completo="Administrador Halu",
                    )
                    return True
                return False

        asegurar_superusuario(get_public_schema_name())
        creado = asegurar_superusuario(schema)
        self.stdout.write(self.style.SUCCESS(
            f"Superusuario {email} {'creado' if creado else 'ya existía'} "
            f"(admin: https://{dominio}/admin)."
        ))

        # 4. Sede inicial.
        with schema_context(schema):
            from apps.atenciones.models import Sede

            Sede.objects.get_or_create(nombre=sede_nombre)
        self.stdout.write(self.style.SUCCESS(f"Sede inicial: {sede_nombre}."))
