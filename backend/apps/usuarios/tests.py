"""
Tests de administración de personal (CLAUDE.md §7 — permisos por rol).

Cubre el alta in-app de médicos/especialistas con su licencia SST, la
segregación por rol (solo el coordinador administra) y la gestión de sedes
y consultorios.
"""
import datetime as dt

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.atenciones.models import Empresa, Sede
from apps.usuarios.models import Profesional, Usuario
from apps.usuarios.roles import Rol


class BasePersonalTest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.sede = Sede.objects.create(nombre="Sede Central")
        self.empresa = Empresa.objects.create(nombre="Empresa X", nit="900-x")
        self.coordinador = Usuario.objects.create_user(
            email="coord@t.co", password="x", nombre_completo="Coord", rol=Rol.COORDINADOR
        )
        self.recepcion = Usuario.objects.create_user(
            email="recep@t.co", password="x", nombre_completo="Recep",
            rol=Rol.RECEPCION, sede=self.sede,
        )
        self.client = TenantClient(self.tenant)

    def _futuro(self, dias=365):
        return (dt.date.today() + dt.timedelta(days=dias)).isoformat()


class AltaPersonalTest(BasePersonalTest):
    def test_coordinador_crea_medico_con_licencia(self):
        self.client.force_login(self.coordinador)
        r = self.client.post("/api/usuarios/", {
            "rol": Rol.MEDICO, "nombre_completo": "Dra. Pérez", "email": "dra@t.co",
            "password": "clave-segura-8", "sede": self.sede.pk,
            "registro_profesional": "RM-123", "especialidad": "Medicina del trabajo",
            "licencia_numero": "LIC-9", "licencia_entidad": "Sec. Salud",
            "licencia_expedicion": "2024-01-01", "licencia_vencimiento": self._futuro(),
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)

        u = Usuario.objects.get(email="dra@t.co")
        self.assertEqual(u.rol, Rol.MEDICO)
        self.assertTrue(u.check_password("clave-segura-8"))
        prof = Profesional.objects.get(usuario=u)
        self.assertEqual(prof.especialidad, "Medicina del trabajo")
        self.assertTrue(prof.tiene_licencia_vigente)
        self.assertTrue(r.json()["tiene_licencia_vigente"])

    def test_medico_sin_sede_es_rechazado(self):
        self.client.force_login(self.coordinador)
        r = self.client.post("/api/usuarios/", {
            "rol": Rol.MEDICO, "nombre_completo": "M", "email": "m2@t.co",
            "password": "clave-segura-8",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("sede", r.json())

    def test_empresa_cliente_requiere_empresa(self):
        self.client.force_login(self.coordinador)
        r = self.client.post("/api/usuarios/", {
            "rol": Rol.EMPRESA_CLIENTE, "nombre_completo": "Portal", "email": "p@t.co",
            "password": "clave-segura-8",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("empresa", r.json())

    def test_recepcion_no_puede_crear_personal(self):
        self.client.force_login(self.recepcion)
        r = self.client.post("/api/usuarios/", {
            "rol": Rol.MEDICO, "nombre_completo": "M", "email": "m3@t.co",
            "password": "clave-segura-8", "sede": self.sede.pk,
        }, content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_admin_sistema_no_aparece_en_directorio(self):
        Usuario.objects.create_superuser(
            email="root@t.co", password="x", nombre_completo="Root"
        )
        self.client.force_login(self.coordinador)
        r = self.client.get("/api/usuarios/")
        correos = [u["email"] for u in r.json()]
        self.assertNotIn("root@t.co", correos)
        self.assertIn("coord@t.co", correos)

    def test_desactivar_usuario(self):
        self.client.force_login(self.coordinador)
        r = self.client.patch(
            f"/api/usuarios/{self.recepcion.pk}/",
            {"is_active": False}, content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.recepcion.refresh_from_db()
        self.assertFalse(self.recepcion.is_active)


class SedesConsultoriosTest(BasePersonalTest):
    def test_coordinador_crea_sede_y_consultorio(self):
        self.client.force_login(self.coordinador)
        rs = self.client.post("/api/sedes/", {"nombre": "Sede Norte"}, content_type="application/json")
        self.assertEqual(rs.status_code, 201, rs.content)
        sede_id = rs.json()["id"]
        rc = self.client.post(
            "/api/consultorios/", {"sede": sede_id, "nombre": "Consultorio 1"},
            content_type="application/json",
        )
        self.assertEqual(rc.status_code, 201, rc.content)
        self.assertEqual(rc.json()["sede_nombre"], "Sede Norte")

    def test_recepcion_lee_pero_no_crea_consultorios(self):
        self.client.force_login(self.recepcion)
        self.assertEqual(self.client.get("/api/consultorios/").status_code, 200)
        r = self.client.post(
            "/api/consultorios/", {"sede": self.sede.pk, "nombre": "X"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
