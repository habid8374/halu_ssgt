"""
Tests obligatorios (CLAUDE.md §7): transiciones de estado de Atencion y
comportamiento append-only de HistorialEstado.
"""
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase

from apps.usuarios.models import Usuario
from apps.usuarios.roles import Rol

from .models import (
    Atencion,
    Empresa,
    EstadoAtencion,
    Sede,
    Trabajador,
    TransicionInvalidaError,
)


class BaseAtencionTest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.sede = Sede.objects.create(nombre="Sede Test")
        self.empresa = Empresa.objects.create(nombre="Empresa Test", nit="900000000-1")
        self.trabajador = Trabajador.objects.create(
            empresa=self.empresa, numero_documento="123", nombres="Test", apellidos="Uno"
        )
        self.recepcion = Usuario.objects.create_user(
            email="r@t.co", password="x", nombre_completo="R", rol=Rol.RECEPCION, sede=self.sede
        )
        self.medico = Usuario.objects.create_user(
            email="m@t.co", password="x", nombre_completo="M", rol=Rol.MEDICO, sede=self.sede
        )
        self.atencion = Atencion.objects.create(
            trabajador=self.trabajador, empresa=self.empresa, sede=self.sede,
            tipo_examen="pre_ingreso", profesional_asignado=self.medico,
            creado_por=self.recepcion,
        )


class TransicionesTest(BaseAtencionTest):
    def test_flujo_completo_valido(self):
        """registrado→espera→llamado→atencion→paraclinicos→finalizado."""
        for estado in ["espera", "llamado", "atencion", "paraclinicos", "finalizado"]:
            self.atencion.cambiar_estado(estado, self.recepcion)
        self.assertEqual(self.atencion.estado, EstadoAtencion.FINALIZADO)
        self.assertEqual(self.atencion.historial_estados.count(), 5)

    def test_no_show_vuelve_a_espera(self):
        self.atencion.cambiar_estado("espera", self.recepcion)
        self.atencion.cambiar_estado("llamado", self.recepcion)
        self.atencion.cambiar_estado("espera", self.recepcion)  # paciente no llegó
        self.assertEqual(self.atencion.estado, EstadoAtencion.ESPERA)

    def test_transicion_invalida_salto(self):
        with self.assertRaises(TransicionInvalidaError):
            self.atencion.cambiar_estado("atencion", self.recepcion)  # salta espera/llamado

    def test_transicion_invalida_mismo_estado(self):
        with self.assertRaises(TransicionInvalidaError):
            self.atencion.cambiar_estado("registrado", self.recepcion)

    def test_finalizado_es_terminal(self):
        for estado in ["espera", "llamado", "atencion", "finalizado"]:
            self.atencion.cambiar_estado(estado, self.recepcion)
        with self.assertRaises(TransicionInvalidaError):
            self.atencion.cambiar_estado("espera", self.recepcion)

    def test_historial_registra_usuario_y_estados(self):
        self.atencion.cambiar_estado("espera", self.recepcion)
        h = self.atencion.historial_estados.get()
        self.assertEqual(h.estado_anterior, EstadoAtencion.REGISTRADO)
        self.assertEqual(h.estado_nuevo, EstadoAtencion.ESPERA)
        self.assertEqual(h.usuario, self.recepcion)


class HistorialAppendOnlyTest(BaseAtencionTest):
    def test_no_update(self):
        self.atencion.cambiar_estado("espera", self.recepcion)
        h = self.atencion.historial_estados.get()
        h.nota = "alterado"
        with self.assertRaises(ValidationError):
            h.save()

    def test_no_delete(self):
        self.atencion.cambiar_estado("espera", self.recepcion)
        h = self.atencion.historial_estados.get()
        with self.assertRaises(ValidationError):
            h.delete()
