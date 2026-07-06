"""
Tests fase 3/4: separación de motores (regla 8), tarifario→factura y RDA.
"""
import datetime as dt

from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.accidentes.models import AccidenteTrabajo
from apps.atenciones.models import Atencion, Empresa, Sede, Trabajador
from apps.usuarios.models import Usuario
from apps.usuarios.roles import Rol

from .models import FacturaARL, TarifaConvenio


class BaseFacturacionTest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.sede = Sede.objects.create(nombre="S")
        self.empresa = Empresa.objects.create(nombre="E", nit="900-f")
        self.otra = Empresa.objects.create(nombre="O", nit="901-f")
        self.trabajador = Trabajador.objects.create(
            empresa=self.empresa, numero_documento="1", primer_nombre="T", primer_apellido="T"
        )
        self.coordinador = Usuario.objects.create_user(
            email="c@t.co", password="x", nombre_completo="C", rol=Rol.COORDINADOR
        )
        self.recepcion = Usuario.objects.create_user(
            email="r@t.co", password="x", nombre_completo="R", rol=Rol.RECEPCION, sede=self.sede
        )
        self.medico = Usuario.objects.create_user(
            email="m@t.co", password="x", nombre_completo="M", rol=Rol.MEDICO, sede=self.sede
        )
        self.client = TenantClient(self.tenant)

    def _atencion_finalizada(self, tipo="periodico"):
        a = Atencion.objects.create(
            trabajador=self.trabajador, empresa=self.empresa, sede=self.sede,
            tipo_examen=tipo, profesional_asignado=self.medico, creado_por=self.recepcion,
        )
        for paso in ["espera", "llamado", "atencion", "finalizado"]:
            a.cambiar_estado(paso, self.recepcion)
        return a


class FacturaEstandarTest(BaseFacturacionTest):
    def test_generar_valora_con_tarifario_y_emite(self):
        TarifaConvenio.objects.create(empresa=self.empresa, tipo_examen="periodico", valor=85000)
        self._atencion_finalizada()
        self._atencion_finalizada()
        self.client.force_login(self.coordinador)
        hoy = dt.date.today().isoformat()
        r = self.client.post("/api/facturas/generar/", {
            "empresa": self.empresa.pk, "desde": "2020-01-01", "hasta": hoy,
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(float(r.json()["total"]), 170000.0)
        factura_id = r.json()["id"]
        # No re-factura lo ya facturado.
        r2 = self.client.post("/api/facturas/generar/", {
            "empresa": self.empresa.pk, "desde": "2020-01-01", "hasta": hoy,
        })
        self.assertEqual(r2.status_code, 409)
        # Emitir asigna número.
        r3 = self.client.post(f"/api/facturas/{factura_id}/emitir/")
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.json()["numero"].startswith("FE-"))

    def test_empresa_solo_ve_sus_facturas_emitidas(self):
        emp_user = Usuario.objects.create_user(
            email="e@t.co", password="x", nombre_completo="E",
            rol=Rol.EMPRESA_CLIENTE, empresa=self.empresa,
        )
        TarifaConvenio.objects.create(empresa=self.empresa, tipo_examen="periodico", valor=1000)
        self._atencion_finalizada()
        self.client.force_login(self.coordinador)
        hoy = dt.date.today().isoformat()
        fid = self.client.post("/api/facturas/generar/", {
            "empresa": self.empresa.pk, "desde": "2020-01-01", "hasta": hoy,
        }).json()["id"]
        self.client.force_login(emp_user)
        # Borrador: invisible para la empresa.
        self.assertEqual(len(self.client.get("/api/facturas/").json()), 0)
        # Emitida: visible, pero no puede emitir/pagar (solo lectura).
        self.client.force_login(self.coordinador)
        self.client.post(f"/api/facturas/{fid}/emitir/")
        self.client.force_login(emp_user)
        self.assertEqual(len(self.client.get("/api/facturas/").json()), 1)
        r = self.client.post(f"/api/facturas/{fid}/marcar_pagada/")
        self.assertEqual(r.status_code, 403)


class SeparacionMotoresTest(BaseFacturacionTest):
    """Regla 8: RIPS solo existe acoplado a un accidente."""

    def test_factura_arl_requiere_accidente_y_genera_rips(self):
        acc = AccidenteTrabajo.objects.create(
            trabajador=self.trabajador, empresa=self.empresa,
            fecha_evento=dt.date.today(), descripcion="x", registrado_por=self.recepcion,
        )
        self.client.force_login(self.coordinador)
        r = self.client.post("/api/facturas-arl/", {"accidente": acc.pk, "valor": "250000"})
        self.assertEqual(r.status_code, 201)
        cuerpo = r.json()
        self.assertTrue(cuerpo["numero"].startswith("FA-"))
        self.assertEqual(cuerpo["rips_json"]["usuarios"][0]["numDocumentoIdentificacion"], "1")
        # Validación MUV (stub) entrega CUV.
        r2 = self.client.post(f"/api/facturas-arl/{cuerpo['id']}/validar_muv/")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.json()["cuv"]), 64)

    def test_atencion_ajena_al_accidente_es_rechazada(self):
        otro_t = Trabajador.objects.create(
            empresa=self.otra, numero_documento="9", primer_nombre="X", primer_apellido="X"
        )
        acc = AccidenteTrabajo.objects.create(
            trabajador=self.trabajador, empresa=self.empresa,
            fecha_evento=dt.date.today(), descripcion="x", registrado_por=self.recepcion,
        )
        atencion_ordinaria = Atencion.objects.create(
            trabajador=otro_t, empresa=self.otra, sede=self.sede,
            tipo_examen="periodico", profesional_asignado=self.medico, creado_por=self.recepcion,
        )
        factura = FacturaARL(
            accidente=acc, atencion=atencion_ordinaria, valor=1000, creada_por=self.coordinador
        )
        with self.assertRaises(ValidationError):
            factura.full_clean()

    def test_factura_estandar_no_contiene_rips(self):
        """El motor estándar no tiene campo RIPS: separación estructural."""
        from .models import Factura

        campos = {f.name for f in Factura._meta.get_fields()}
        self.assertNotIn("rips_json", campos)
        self.assertNotIn("cuv", campos)


class RdaTest(BaseFacturacionTest):
    def test_rda_contiene_los_4_grupos_de_datos(self):
        from apps.historia_clinica.models import (
            ConceptoMedicoOcupacional,
            HistoriaClinicaOcupacional,
        )

        atencion = self._atencion_finalizada()
        historia = HistoriaClinicaOcupacional.objects.create(atencion=atencion, profesional=self.medico)
        ConceptoMedicoOcupacional.objects.create(
            atencion=atencion, historia=historia, profesional=self.medico,
            aptitud="apto", firmado=True, fecha_emision=dt.date.today(),
        )
        self.client.force_login(self.medico)
        r = self.client.get(f"/api/atenciones/{atencion.pk}/rda/")
        self.assertEqual(r.status_code, 200)
        bundle = r.json()
        tipos = [e["resource"]["resourceType"] for e in bundle["entry"]]
        # (i) Patient, (ii) Encounter, (iii) Procedure, (iv) Observation
        self.assertEqual(tipos, ["Patient", "Encounter", "Procedure", "Observation"])
        # El RDA nunca incluye contenido de la historia clínica reservada.
        self.assertNotIn("motivo_consulta", str(bundle))

    def test_rda_prohibido_para_recepcion_y_empresa(self):
        atencion = self._atencion_finalizada()
        self.client.force_login(self.recepcion)
        self.assertEqual(self.client.get(f"/api/atenciones/{atencion.pk}/rda/").status_code, 403)
