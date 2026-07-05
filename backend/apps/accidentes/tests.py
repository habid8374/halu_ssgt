"""
Tests obligatorios de fase 2 (CLAUDE.md §7): generación de alertas de plazo
(FURAT 2 días hábiles y adaptación 20 días hábiles) y días hábiles.
"""
import datetime as dt

from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.atenciones.models import Atencion, Empresa, Sede, Trabajador
from apps.historia_clinica.models import (
    ConceptoMedicoOcupacional,
    HistoriaClinicaOcupacional,
)
from apps.usuarios.models import Usuario
from apps.usuarios.roles import Rol

from .models import AccidenteTrabajo, Alerta, ReporteFURAT
from .tasks import _revisar_tenant
from .utils import dias_habiles_entre, sumar_dias_habiles


class DiasHabilesTest(TenantTestCase):
    def test_suma_salta_fin_de_semana(self):
        # Viernes 2026-07-03 + 2 días hábiles = martes 2026-07-07
        self.assertEqual(sumar_dias_habiles(dt.date(2026, 7, 3), 2), dt.date(2026, 7, 7))

    def test_entre(self):
        self.assertEqual(dias_habiles_entre(dt.date(2026, 7, 3), dt.date(2026, 7, 7)), 2)


class BaseFase2Test(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.sede = Sede.objects.create(nombre="Sede T")
        self.empresa = Empresa.objects.create(nombre="Empresa T", nit="900-t")
        self.trabajador = Trabajador.objects.create(
            empresa=self.empresa, numero_documento="1", nombres="T", apellidos="T"
        )
        self.coordinador = Usuario.objects.create_user(
            email="c@t.co", password="x", nombre_completo="C", rol=Rol.COORDINADOR
        )
        self.recepcion = Usuario.objects.create_user(
            email="r@t.co", password="x", nombre_completo="R", rol=Rol.RECEPCION, sede=self.sede
        )


class AlertaFuratTest(BaseFase2Test):
    def test_reporte_furat_calcula_plazo_2_dias_habiles(self):
        acc = AccidenteTrabajo.objects.create(
            trabajador=self.trabajador, empresa=self.empresa,
            fecha_evento=dt.date(2026, 7, 3),  # viernes
            descripcion="x", registrado_por=self.recepcion,
        )
        rep = ReporteFURAT.objects.create(accidente=acc)
        self.assertEqual(rep.fecha_limite, dt.date(2026, 7, 7))  # martes

    def test_alerta_por_vencer_y_vencida(self):
        hoy = timezone.localdate()
        acc = AccidenteTrabajo.objects.create(
            trabajador=self.trabajador, empresa=self.empresa,
            fecha_evento=hoy - dt.timedelta(days=10),  # plazo ya vencido
            descripcion="x", registrado_por=self.recepcion,
        )
        ReporteFURAT.objects.create(accidente=acc)
        _revisar_tenant(hoy)
        alerta = Alerta.objects.get(tipo="furat")
        self.assertTrue(alerta.vencida)
        self.assertIn("VENCIDO", alerta.mensaje)
        # Idempotente: correr de nuevo no duplica.
        _revisar_tenant(hoy)
        self.assertEqual(Alerta.objects.filter(tipo="furat").count(), 1)

    def test_alerta_se_resuelve_al_enviar_reporte(self):
        hoy = timezone.localdate()
        acc = AccidenteTrabajo.objects.create(
            trabajador=self.trabajador, empresa=self.empresa,
            fecha_evento=hoy - dt.timedelta(days=10),
            descripcion="x", registrado_por=self.recepcion,
        )
        rep = ReporteFURAT.objects.create(accidente=acc)
        _revisar_tenant(hoy)
        rep.marcar_enviado(radicado="RAD-1")
        _revisar_tenant(hoy)
        self.assertTrue(Alerta.objects.get(tipo="furat").resuelta)


class AlertaAdaptacionTest(BaseFase2Test):
    def test_alerta_20_dias_habiles(self):
        medico = Usuario.objects.create_user(
            email="m@t.co", password="x", nombre_completo="M", rol=Rol.MEDICO, sede=self.sede
        )
        atencion = Atencion.objects.create(
            trabajador=self.trabajador, empresa=self.empresa, sede=self.sede,
            tipo_examen="periodico", profesional_asignado=medico, creado_por=self.recepcion,
        )
        historia = HistoriaClinicaOcupacional.objects.create(atencion=atencion, profesional=medico)
        hoy = timezone.localdate()
        ConceptoMedicoOcupacional.objects.create(
            atencion=atencion, historia=historia, profesional=medico,
            aptitud="apto_restricciones", firmado=True,
            fecha_recomendacion=hoy - dt.timedelta(days=40),  # 20 días hábiles ya vencidos
        )
        _revisar_tenant(hoy)
        alerta = Alerta.objects.get(tipo="adaptacion")
        self.assertTrue(alerta.vencida)

        # Al marcar el seguimiento, la alerta se resuelve.
        ConceptoMedicoOcupacional.objects.update(seguimiento_completado=True)
        _revisar_tenant(hoy)
        alerta.refresh_from_db()
        self.assertTrue(alerta.resuelta)


class PermisosAccidentesTest(BaseFase2Test):
    def test_empresa_cliente_sin_acceso(self):
        emp_user = Usuario.objects.create_user(
            email="e@t.co", password="x", nombre_completo="E",
            rol=Rol.EMPRESA_CLIENTE, empresa=self.empresa,
        )
        client = TenantClient(self.tenant)
        client.force_login(emp_user)
        self.assertEqual(client.get("/api/accidentes/").status_code, 403)
        self.assertEqual(client.get("/api/alertas/").status_code, 403)

    def test_coordinador_marca_enviado(self):
        client = TenantClient(self.tenant)
        client.force_login(self.recepcion)
        r = client.post("/api/accidentes/", {
            "tipo_evento": "accidente", "trabajador": self.trabajador.pk,
            "fecha_evento": "2026-07-01", "gravedad": "leve", "descripcion": "caída",
        })
        self.assertEqual(r.status_code, 201)
        acc_id = r.json()["id"]
        self.assertEqual(r.json()["reporte"]["estado"], "pendiente")
        # Recepción NO puede marcar enviado…
        r = client.post(f"/api/accidentes/{acc_id}/marcar_enviado/", {"radicado": "X"})
        self.assertEqual(r.status_code, 403)
        # …el coordinador sí.
        client.force_login(self.coordinador)
        r = client.post(f"/api/accidentes/{acc_id}/marcar_enviado/", {"radicado": "RAD-9"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["reporte"]["estado"], "enviado")
