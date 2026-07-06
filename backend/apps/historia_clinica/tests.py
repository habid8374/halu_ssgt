"""
Tests obligatorios (CLAUDE.md §7): permisos por rol sobre historia clínica
y concepto — la parte legalmente crítica (reglas 1, 5 y 9).
"""
import datetime as dt

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.atenciones.models import Atencion, Empresa, Sede, Trabajador
from apps.usuarios.models import AuditLog, LicenciaSST, Profesional, Usuario
from apps.usuarios.roles import Rol

from .models import ConceptoMedicoOcupacional, HistoriaClinicaOcupacional


class BasePermisosTest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        self.sede = Sede.objects.create(nombre="Sede Test")
        self.empresa = Empresa.objects.create(nombre="Empresa A", nit="900000000-1")
        self.otra_empresa = Empresa.objects.create(nombre="Empresa B", nit="900000000-2")

        def u(email, rol, **extra):
            return Usuario.objects.create_user(
                email=email, password="x", nombre_completo=email, rol=rol, **extra
            )

        self.recepcion = u("r@t.co", Rol.RECEPCION, sede=self.sede)
        self.medico = u("m@t.co", Rol.MEDICO, sede=self.sede)
        self.otro_medico = u("m2@t.co", Rol.MEDICO, sede=self.sede)
        self.coordinador = u("c@t.co", Rol.COORDINADOR)
        self.empresa_user = u("e@t.co", Rol.EMPRESA_CLIENTE, empresa=self.empresa)

        self.trabajador = Trabajador.objects.create(
            empresa=self.empresa, numero_documento="123", primer_nombre="Juan", primer_apellido="Pérez"
        )
        self.atencion = Atencion.objects.create(
            trabajador=self.trabajador, empresa=self.empresa, sede=self.sede,
            tipo_examen="pre_ingreso", profesional_asignado=self.medico,
            creado_por=self.recepcion,
        )
        self.historia = HistoriaClinicaOcupacional.objects.create(
            atencion=self.atencion, profesional=self.medico, motivo_consulta="Reservado"
        )
        self.concepto = ConceptoMedicoOcupacional.objects.create(
            atencion=self.atencion, historia=self.historia, profesional=self.medico,
            aptitud="apto", firmado=True, fecha_emision=dt.date.today(),
        )

    def _get(self, user, url):
        self.client.force_login(user)
        return self.client.get(url)


class HistoriaClinicaPermisosTest(BasePermisosTest):
    URL = "/api/historias/"

    def test_empresa_cliente_NUNCA_ve_historia(self):
        """Regla 1 — Res. 1843/2025: denegación incondicional."""
        r = self._get(self.empresa_user, self.URL)
        self.assertEqual(r.status_code, 403)
        r = self._get(self.empresa_user, f"{self.URL}{self.historia.pk}/")
        self.assertEqual(r.status_code, 403)

    def test_recepcion_no_ve_historia(self):
        self.assertEqual(self._get(self.recepcion, self.URL).status_code, 403)

    def test_coordinador_no_ve_historia(self):
        self.assertEqual(self._get(self.coordinador, self.URL).status_code, 403)

    def test_medico_asignado_si_ve(self):
        r = self._get(self.medico, f"{self.URL}{self.historia.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["motivo_consulta"], "Reservado")

    def test_medico_NO_asignado_no_ve(self):
        """Médico solo pacientes asignados (§4): queryset scoping → 404."""
        r = self._get(self.otro_medico, f"{self.URL}{self.historia.pk}/")
        self.assertEqual(r.status_code, 404)

    def test_lectura_queda_auditada(self):
        """Regla 9: toda lectura de historia clínica genera AuditLog."""
        antes = AuditLog.objects.count()
        self._get(self.medico, f"{self.URL}{self.historia.pk}/")
        self.assertEqual(AuditLog.objects.count(), antes + 1)
        log = AuditLog.objects.latest("timestamp")
        self.assertEqual(log.accion, "ver")
        self.assertIn("HistoriaClinicaOcupacional", log.modelo)


class ConceptoPermisosTest(BasePermisosTest):
    URL = "/api/conceptos/"

    def test_empresa_ve_concepto_firmado_de_su_trabajador(self):
        r = self._get(self.empresa_user, f"{self.URL}{self.concepto.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["aptitud"], "apto")

    def test_concepto_no_expone_campos_clinicos(self):
        """Separación por diseño: el payload del concepto no contiene historia."""
        r = self._get(self.empresa_user, f"{self.URL}{self.concepto.pk}/")
        for campo in ("motivo_consulta", "diagnosticos", "examen_fisico", "antecedentes"):
            self.assertNotIn(campo, r.json())

    def test_empresa_NO_ve_conceptos_de_otra_empresa(self):
        otro_t = Trabajador.objects.create(
            empresa=self.otra_empresa, numero_documento="456", primer_nombre="Ana", primer_apellido="Gil"
        )
        otra_a = Atencion.objects.create(
            trabajador=otro_t, empresa=self.otra_empresa, sede=self.sede,
            tipo_examen="egreso", profesional_asignado=self.medico, creado_por=self.recepcion,
        )
        otra_h = HistoriaClinicaOcupacional.objects.create(atencion=otra_a, profesional=self.medico)
        otro_c = ConceptoMedicoOcupacional.objects.create(
            atencion=otra_a, historia=otra_h, profesional=self.medico,
            aptitud="apto", firmado=True,
        )
        r = self._get(self.empresa_user, f"{self.URL}{otro_c.pk}/")
        self.assertEqual(r.status_code, 404)  # scoping: ni existe para ella

    def test_empresa_NO_ve_concepto_sin_firmar(self):
        self.concepto.firmado = False
        self.concepto.save(update_fields=["firmado"])
        r = self._get(self.empresa_user, f"{self.URL}{self.concepto.pk}/")
        self.assertEqual(r.status_code, 404)

    def test_empresa_no_puede_modificar_concepto(self):
        self.client.force_login(self.empresa_user)
        r = self.client.patch(
            f"{self.URL}{self.concepto.pk}/", {"aptitud": "no_apto"},
            content_type="application/json",
        )
        self.assertIn(r.status_code, (403, 405))


class FirmaConceptoTest(BasePermisosTest):
    def test_firma_requiere_licencia_sst_vigente(self):
        """Regla 5 — Res. 4502/2012: sin licencia vigente no hay firma."""
        concepto = ConceptoMedicoOcupacional.objects.create(
            atencion=Atencion.objects.create(
                trabajador=self.trabajador, empresa=self.empresa, sede=self.sede,
                tipo_examen="periodico", profesional_asignado=self.medico,
                creado_por=self.recepcion,
            ),
            historia=HistoriaClinicaOcupacional.objects.create(
                atencion=Atencion.objects.latest("id"), profesional=self.medico
            ),
            profesional=self.medico, aptitud="apto",
        )
        self.client.force_login(self.medico)
        # Sin perfil profesional/licencia → rechazo.
        r = self.client.post(f"/api/conceptos/{concepto.pk}/firmar/")
        self.assertEqual(r.status_code, 400)

        # Con licencia vencida → rechazo.
        prof = Profesional.objects.create(usuario=self.medico, tipo="medico")
        LicenciaSST.objects.create(
            profesional=prof, numero="L-1", entidad_expide="SS",
            fecha_expedicion=dt.date(2020, 1, 1),
            fecha_vencimiento=dt.date(2021, 1, 1), validada=True,
        )
        r = self.client.post(f"/api/conceptos/{concepto.pk}/firmar/")
        self.assertEqual(r.status_code, 400)

        # Con licencia vigente y validada → firma OK y queda referenciada.
        lic = LicenciaSST.objects.create(
            profesional=prof, numero="L-2", entidad_expide="SS",
            fecha_expedicion=dt.date.today(),
            fecha_vencimiento=dt.date.today() + dt.timedelta(days=365), validada=True,
        )
        r = self.client.post(f"/api/conceptos/{concepto.pk}/firmar/")
        self.assertEqual(r.status_code, 200)
        concepto.refresh_from_db()
        self.assertTrue(concepto.firmado)
        self.assertEqual(concepto.licencia_sst, lic)


class ModuloMedicoTest(BasePermisosTest):
    """Diagnósticos CIE, órdenes y recetas: reservados al médico asignado."""

    def test_medico_asignado_crea_diagnostico(self):
        self.client.force_login(self.medico)
        r = self.client.post("/api/diagnosticos/", {
            "historia": self.historia.pk,
            "cie10_codigo": "Z100", "cie10_desc": "Examen de salud ocupacional",
            "cie11_codigo": "QA00", "relacion": "principal", "tipo": "02",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["cie10_codigo"], "Z100")

    def test_otro_medico_no_diagnostica_historia_ajena(self):
        self.client.force_login(self.otro_medico)
        r = self.client.post("/api/diagnosticos/", {
            "historia": self.historia.pk,
            "cie10_codigo": "Z100", "cie10_desc": "X",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)  # validate_historia

    def test_recepcion_no_crea_ordenes_ni_recetas(self):
        self.client.force_login(self.recepcion)
        r = self.client.post("/api/ordenes/", {
            "atencion": self.atencion.pk, "tipo": "laboratorio", "descripcion": "Hemograma",
        }, content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_medico_crea_orden_y_solo_el_la_ve(self):
        self.client.force_login(self.medico)
        r = self.client.post("/api/ordenes/", {
            "atencion": self.atencion.pk, "tipo": "imagen",
            "descripcion": "RX de tórax", "cantidad": 1,
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        # El médico asignado la ve; el otro médico no (scoping).
        self.assertEqual(len(self._get(self.medico, f"/api/ordenes/?atencion={self.atencion.pk}").json()), 1)
        self.assertEqual(len(self._get(self.otro_medico, f"/api/ordenes/?atencion={self.atencion.pk}").json()), 0)

    def test_receta_con_medicamentos(self):
        self.client.force_login(self.medico)
        r = self.client.post("/api/recetas/", {
            "atencion": self.atencion.pk, "observaciones": "Tomar con alimentos",
            "medicamentos": [
                {"medicamento": "Acetaminofén", "concentracion": "500 mg",
                 "dosis": "1 tableta", "frecuencia": "cada 8 horas", "duracion": "5 días"},
            ],
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.json()["medicamentos"]), 1)

    def test_receta_sin_medicamentos_rechazada(self):
        self.client.force_login(self.medico)
        r = self.client.post("/api/recetas/", {
            "atencion": self.atencion.pk, "medicamentos": [],
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)


class PsicosocialCustodiaTest(BasePermisosTest):
    """Regla 4 (Res. 2404/2019): custodia separada de instrumentos."""

    def setUp(self):
        super().setUp()
        from apps.usuarios.models import Usuario

        self.psicologo = Usuario.objects.create_user(
            email="p@t.co", password="x", nombre_completo="P",
            rol=Rol.PSICOLOGO_SST, sede=self.sede,
        )
        self.otro_psicologo = Usuario.objects.create_user(
            email="p2@t.co", password="x", nombre_completo="P2",
            rol=Rol.PSICOLOGO_SST, sede=self.sede,
        )
        from .models import InstrumentoPsicosocial

        self.instrumento = InstrumentoPsicosocial.objects.create(
            trabajador=self.trabajador, tipo="intralaboral",
            aplicado_por=self.psicologo, nivel_riesgo="alto",
            contenido="respuestas individuales reservadas",
        )

    def test_solo_el_psicologo_que_aplico_ve_el_instrumento(self):
        url = f"/api/psicosocial/instrumentos/{self.instrumento.pk}/"
        r = self._get(self.psicologo, url)
        self.assertEqual(r.status_code, 200)
        # Otro psicólogo: fuera de su custodia -> 404 por scoping.
        self.assertEqual(self._get(self.otro_psicologo, url).status_code, 404)
        # Empresa, coordinador y médico: prohibido.
        self.assertEqual(self._get(self.empresa_user, url).status_code, 403)
        self.assertEqual(self._get(self.coordinador, url).status_code, 403)
        self.assertEqual(self._get(self.medico, url).status_code, 403)

    def test_consolidado_agregado_sin_individuales(self):
        from .models import InstrumentoPsicosocial

        for i in range(3):
            t = Trabajador.objects.create(
                empresa=self.empresa, numero_documento=f"c{i}", primer_nombre="X", primer_apellido="Y"
            )
            InstrumentoPsicosocial.objects.create(
                trabajador=t, tipo="estres", aplicado_por=self.psicologo, nivel_riesgo="medio"
            )
        r = self._get(self.empresa_user, "/api/psicosocial/consolidado/")
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(cuerpo["total"], 4)
        # Solo agregados: nunca contenido ni identificación individual.
        self.assertNotIn("contenido", str(cuerpo))
        self.assertTrue(all(set(d) == {"tipo", "nivel_riesgo", "cantidad"} for d in cuerpo["detalle"]))

    def test_consolidado_respeta_minimo_anonimato(self):
        r = self._get(self.empresa_user, "/api/psicosocial/consolidado/")
        # Solo hay 1 instrumento de su empresa: no se entrega detalle.
        self.assertEqual(r.json()["detalle"], [])
