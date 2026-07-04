"""
Datos de demostración para desarrollo. Idempotente: se puede correr N veces.

Crea:
  - Tenant público (routing) y tenant "demo" mapeado a localhost.
  - Sede Principal con 2 consultorios.
  - Usuarios por rol (password: demo1234):
      recepcion@demo.com, medico@demo.com, coordinador@demo.com, empresa@demo.com
  - Médico con licencia SST vigente y validada.
  - 2 empresas cliente, 8 trabajadores y atenciones en varios estados
    para que el tablero se vea vivo.

NUNCA usar en producción (los datos y contraseñas son de juguete).
"""
import datetime as dt

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from apps.tenants.models import IPS, Dominio


class Command(BaseCommand):
    help = "Crea tenant demo + datos de ejemplo para el tablero (solo desarrollo)."

    def handle(self, *args, **options):
        # --- 1. Tenants ----------------------------------------------------
        publico, _ = IPS.objects.get_or_create(
            schema_name="public",
            defaults={"nombre": "Public", "nit": "000000000-0"},
        )
        demo, creado = IPS.objects.get_or_create(
            schema_name="demo",
            defaults={"nombre": "IPS Demo Salud Ocupacional", "nit": "900123456-7"},
        )
        for host in ("localhost", "127.0.0.1", "web"):
            Dominio.objects.get_or_create(
                domain=host, defaults={"tenant": demo, "is_primary": host == "localhost"}
            )
        self.stdout.write(self.style.SUCCESS(f"Tenant demo {'creado' if creado else 'ya existía'}."))

        # --- 2. Datos dentro del esquema demo -------------------------------
        with schema_context("demo"):
            self._seed_demo()

    def _seed_demo(self):
        from apps.atenciones.models import (
            Atencion,
            Consultorio,
            Empresa,
            EstadoAtencion,
            Sede,
            Trabajador,
        )
        from apps.usuarios.models import LicenciaSST, Profesional, Usuario
        from apps.usuarios.roles import Rol

        sede, _ = Sede.objects.get_or_create(nombre="Sede Principal", defaults={"codigo": "SP"})
        c1, _ = Consultorio.objects.get_or_create(sede=sede, nombre="Consultorio 1")
        c2, _ = Consultorio.objects.get_or_create(sede=sede, nombre="Consultorio 2")

        def usuario(email, nombre, rol, **extra):
            u = Usuario.objects.filter(email=email).first()
            if u is None:
                u = Usuario.objects.create_user(
                    email=email, password="demo1234", nombre_completo=nombre, rol=rol, **extra
                )
            return u

        recepcion = usuario("recepcion@demo.com", "Rosa Recepción", Rol.RECEPCION, sede=sede)
        medico = usuario("medico@demo.com", "Dr. Mario Médico", Rol.MEDICO, sede=sede)
        usuario("coordinador@demo.com", "Carla Coordinadora", Rol.COORDINADOR)

        empresa1, _ = Empresa.objects.get_or_create(
            nit="800111222-3", defaults={"nombre": "Constructora Andina S.A.S."}
        )
        empresa2, _ = Empresa.objects.get_or_create(
            nit="800444555-6", defaults={"nombre": "Alimentos del Valle Ltda."}
        )
        usuario("empresa@demo.com", "Portal Constructora Andina", Rol.EMPRESA_CLIENTE, empresa=empresa1)

        # Médico con licencia SST vigente (regla 5) para poder firmar conceptos.
        prof, _ = Profesional.objects.get_or_create(
            usuario=medico, defaults={"tipo": "medico", "registro_profesional": "RM-12345"}
        )
        LicenciaSST.objects.get_or_create(
            profesional=prof,
            numero="SST-2024-001",
            defaults={
                "entidad_expide": "Secretaría de Salud",
                "fecha_expedicion": dt.date(2024, 1, 15),
                "fecha_vencimiento": dt.date.today() + dt.timedelta(days=365 * 5),
                "validada": True,
            },
        )

        trabajadores_data = [
            (empresa1, "1010101010", "Juan", "Pérez Gómez", "Oficial de obra"),
            (empresa1, "1010101011", "María", "Rodríguez López", "Maestra de obra"),
            (empresa1, "1010101012", "Carlos", "Sánchez Díaz", "Ayudante"),
            (empresa1, "1010101013", "Luisa", "Martínez Vega", "Ingeniera residente"),
            (empresa2, "2020202020", "Andrés", "Castro Ruiz", "Operario de planta"),
            (empresa2, "2020202021", "Paola", "Jiménez Torres", "Supervisora de calidad"),
            (empresa2, "2020202022", "Diego", "Moreno Silva", "Auxiliar de bodega"),
            (empresa2, "2020202023", "Sandra", "Gil Ramírez", "Analista de laboratorio"),
        ]
        trabajadores = []
        for empresa, doc, nombres, apellidos, cargo in trabajadores_data:
            t, _ = Trabajador.objects.get_or_create(
                tipo_documento="CC",
                numero_documento=doc,
                defaults={
                    "empresa": empresa, "nombres": nombres,
                    "apellidos": apellidos, "cargo": cargo,
                },
            )
            trabajadores.append(t)

        if Atencion.objects.exists():
            self.stdout.write("Atenciones demo ya existen; no se duplican.")
            return

        # Atenciones repartidas por estados para que el tablero se vea vivo.
        # Se crean vía cambiar_estado() para respetar la máquina de estados
        # y dejar HistorialEstado coherente.
        planes = [
            ("pre_ingreso", []),                                            # registrado
            ("periodico", ["espera"]),
            ("pre_ingreso", ["espera"]),
            ("egreso", ["espera", "llamado"]),
            ("periodico", ["espera", "llamado", "atencion"]),
            ("pre_ingreso", ["espera", "llamado", "atencion", "paraclinicos"]),
            ("periodico", ["espera", "llamado", "atencion", "finalizado"]),
            ("retorno_laboral", ["espera"]),
        ]
        for t, (tipo, pasos) in zip(trabajadores, planes):
            a = Atencion.objects.create(
                trabajador=t, empresa=t.empresa, sede=sede,
                consultorio=c1 if t.empresa_id % 2 else c2,
                tipo_examen=tipo, profesional_asignado=medico, creado_por=recepcion,
            )
            for paso in pasos:
                usuario_paso = recepcion if paso in {"espera", "llamado"} else medico
                a.cambiar_estado(paso, usuario_paso, nota="seed demo")

        self.stdout.write(self.style.SUCCESS(
            f"Seed demo listo: {Atencion.objects.count()} atenciones en sede '{sede.nombre}'."
        ))
        self.stdout.write("Usuarios (password demo1234): recepcion@ / medico@ / coordinador@ / empresa@demo.com")
