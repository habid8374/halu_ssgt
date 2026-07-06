"""
Datos de demostración para desarrollo. Idempotente: se puede correr N veces.

Crea:
  - Tenant público + dominio de administración (admin.localhost) con
    superusuario admin@halu.co / admin1234 para gestionar IPS y dominios.
  - IPS "demo"  -> localhost / 127.0.0.1  (IPS Demo Salud Ocupacional)
  - IPS "demo2" -> demo2.localhost        (IPS Norte SST) — demuestra el
    aislamiento multi-tenant: cada dominio ve SOLO sus datos.
  - En cada IPS: sede, consultorios, usuarios por rol (password demo1234),
    médico con licencia SST vigente, empresas, trabajadores y atenciones.

NUNCA usar en producción (los datos y contraseñas son de juguete).
"""
import datetime as dt

from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import IPS, Dominio


class Command(BaseCommand):
    help = "Crea tenants demo + datos de ejemplo (solo desarrollo)."

    def handle(self, *args, **options):
        # --- 1. Tenant público + admin de plataforma ------------------------
        publico, _ = IPS.objects.get_or_create(
            schema_name=get_public_schema_name(),
            defaults={"nombre": "Plataforma Halu", "nit": "000000000-0"},
        )
        Dominio.objects.get_or_create(
            domain="admin.localhost", defaults={"tenant": publico, "is_primary": True}
        )
        with schema_context(get_public_schema_name()):
            from apps.usuarios.models import Usuario

            if not Usuario.objects.filter(email="admin@halu.co").exists():
                Usuario.objects.create_superuser(
                    email="admin@halu.co", password="admin1234",
                    nombre_completo="Admin Plataforma",
                )
        self.stdout.write(self.style.SUCCESS(
            "Admin de plataforma: http://admin.localhost:8000/admin (admin@halu.co / admin1234)"
        ))

        # --- 2. IPS demo (localhost) ----------------------------------------
        demo, _ = IPS.objects.get_or_create(
            schema_name="demo",
            defaults={"nombre": "IPS Demo Salud Ocupacional", "nit": "900123456-7"},
        )
        for host in ("localhost", "127.0.0.1", "web"):
            Dominio.objects.get_or_create(
                domain=host, defaults={"tenant": demo, "is_primary": host == "localhost"}
            )
        with schema_context("demo"):
            self._seed_ips(
                dominio_correo="demo.com",
                sede_nombre="Sede Principal",
                empresas=[
                    ("Constructora Andina S.A.S.", "800111222-3"),
                    ("Alimentos del Valle Ltda.", "800444555-6"),
                ],
                trabajadores=[
                    (0, "1010101010", "Juan", "Pérez Gómez", "Oficial de obra"),
                    (0, "1010101011", "María", "Rodríguez López", "Maestra de obra"),
                    (0, "1010101012", "Carlos", "Sánchez Díaz", "Ayudante"),
                    (0, "1010101013", "Luisa", "Martínez Vega", "Ingeniera residente"),
                    (1, "2020202020", "Andrés", "Castro Ruiz", "Operario de planta"),
                    (1, "2020202021", "Paola", "Jiménez Torres", "Supervisora de calidad"),
                    (1, "2020202022", "Diego", "Moreno Silva", "Auxiliar de bodega"),
                    (1, "2020202023", "Sandra", "Gil Ramírez", "Analista de laboratorio"),
                ],
            )

        # --- 3. IPS demo2 (demo2.localhost): aislamiento multi-tenant -------
        demo2, _ = IPS.objects.get_or_create(
            schema_name="demo2",
            defaults={"nombre": "IPS Norte SST", "nit": "901987654-3"},
        )
        Dominio.objects.get_or_create(
            domain="demo2.localhost", defaults={"tenant": demo2, "is_primary": True}
        )
        with schema_context("demo2"):
            self._seed_ips(
                dominio_correo="demo2.com",
                sede_nombre="Sede Norte",
                empresas=[
                    ("Minera del Norte S.A.", "890555666-1"),
                    ("Transportes La Sabana S.A.S.", "890777888-2"),
                ],
                trabajadores=[
                    (0, "3030303030", "Elena", "Vargas Prieto", "Geóloga"),
                    (0, "3030303031", "Óscar", "Rincón Mesa", "Operador de maquinaria"),
                    (1, "4040404040", "Lucía", "Camargo Peña", "Conductora"),
                    (1, "4040404041", "Felipe", "Núñez Rey", "Despachador"),
                ],
            )

        self.stdout.write(self.style.SUCCESS(
            "Tenants demo listos: localhost (IPS Demo) y demo2.localhost (IPS Norte SST)."
        ))

    # ------------------------------------------------------------------
    def _seed_ips(self, dominio_correo, sede_nombre, empresas, trabajadores):
        from apps.atenciones.models import (
            Atencion,
            Consultorio,
            Empresa,
            Sede,
            Trabajador,
        )
        from apps.usuarios.models import LicenciaSST, Profesional, Usuario
        from apps.usuarios.roles import Rol

        sede, _ = Sede.objects.get_or_create(nombre=sede_nombre)
        c1, _ = Consultorio.objects.get_or_create(sede=sede, nombre="Consultorio 1")
        c2, _ = Consultorio.objects.get_or_create(sede=sede, nombre="Consultorio 2")

        def usuario(email, nombre, rol, **extra):
            u = Usuario.objects.filter(email=email).first()
            if u is None:
                u = Usuario.objects.create_user(
                    email=email, password="demo1234", nombre_completo=nombre, rol=rol, **extra
                )
            return u

        recepcion = usuario(f"recepcion@{dominio_correo}", "Rosa Recepción", Rol.RECEPCION, sede=sede)
        medico = usuario(f"medico@{dominio_correo}", "Dr. Mario Médico", Rol.MEDICO, sede=sede)
        usuario(f"coordinador@{dominio_correo}", "Carla Coordinadora", Rol.COORDINADOR)
        psicologo = usuario(f"psicologo@{dominio_correo}", "Psi. Paula Psicóloga", Rol.PSICOLOGO_SST, sede=sede)
        prof_psi, _ = Profesional.objects.get_or_create(
            usuario=psicologo, defaults={"tipo": "psicologo", "registro_profesional": "PSI-9876"}
        )
        LicenciaSST.objects.get_or_create(
            profesional=prof_psi, numero="SST-2024-002",
            defaults={
                "entidad_expide": "Secretaría de Salud",
                "fecha_expedicion": dt.date(2024, 1, 15),
                "fecha_vencimiento": dt.date.today() + dt.timedelta(days=365 * 5),
                "validada": True,
            },
        )

        from apps.facturacion.models import TarifaConvenio

        objetos_empresa = []
        for nombre, nit in empresas:
            e, _ = Empresa.objects.get_or_create(nit=nit, defaults={
                "nombre": nombre, "digito_verificacion": "1",
                "actividad_economica_ciiu": "4290", "actividad_economica_desc": "Construcción de obras de ingeniería",
                "clase_riesgo": "V", "arl_nombre": "Positiva",
                "departamento": "Cundinamarca", "municipio": "Bogotá D.C.", "municipio_dane": "11001",
                "direccion": "Calle 100 # 15-20", "telefono": "6015551234",
                "representante_legal": "Representante Legal Demo",
                "responsable_sst": "Responsable SST Demo",
            })
            objetos_empresa.append(e)
            # Tarifario demo del convenio.
            for tipo, valor in [
                ("pre_ingreso", 95000), ("periodico", 85000), ("egreso", 80000),
                ("post_incapacidad", 90000), ("retorno_laboral", 90000), ("seguimiento", 70000),
            ]:
                TarifaConvenio.objects.get_or_create(
                    empresa=e, tipo_examen=tipo, defaults={"valor": valor}
                )
        usuario(
            f"empresa@{dominio_correo}", f"Portal {objetos_empresa[0].nombre}",
            Rol.EMPRESA_CLIENTE, empresa=objetos_empresa[0],
        )

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

        objetos_trabajador = []
        for idx_empresa, doc, nombres, apellidos, cargo in trabajadores:
            pn, _, sn = nombres.partition(" ")
            pa, _, sa = apellidos.partition(" ")
            t, _ = Trabajador.objects.get_or_create(
                tipo_documento="CC",
                numero_documento=doc,
                defaults={
                    "empresa": objetos_empresa[idx_empresa],
                    "primer_nombre": pn, "segundo_nombre": sn,
                    "primer_apellido": pa, "segundo_apellido": sa,
                    "cargo": cargo, "sexo": "M",
                    "fecha_nacimiento": dt.date(1990, 1, 1),
                    "municipio_residencia": "Bogotá D.C.", "municipio_dane": "11001",
                    "zona_territorial": "U", "tipo_afiliacion": "contributivo",
                },
            )
            objetos_trabajador.append(t)

        if Atencion.objects.exists():
            return

        tipos = ["pre_ingreso", "periodico", "egreso", "retorno_laboral"]
        planes = [
            [],                                              # registrado
            ["espera"],
            ["espera", "llamado"],
            ["espera", "llamado", "atencion"],
            ["espera"],
            ["espera", "llamado", "atencion", "paraclinicos"],
            ["espera", "llamado", "atencion", "finalizado"],
            ["espera"],
        ]
        for i, t in enumerate(objetos_trabajador):
            a = Atencion.objects.create(
                trabajador=t, empresa=t.empresa, sede=sede,
                consultorio=c1 if i % 2 else c2,
                tipo_examen=tipos[i % len(tipos)],
                profesional_asignado=medico, creado_por=recepcion,
            )
            for paso in planes[i % len(planes)]:
                quien = recepcion if paso in {"espera", "llamado"} else medico
                a.cambiar_estado(paso, quien, nota="seed demo")

        self.stdout.write(
            f"  {sede_nombre}: {Atencion.objects.count()} atenciones, "
            f"usuarios *@{dominio_correo} (password demo1234)"
        )
