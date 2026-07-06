from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sedes", views.SedeViewSet, basename="sede")
router.register("consultorios", views.ConsultorioViewSet, basename="consultorio")
router.register("empresas", views.EmpresaViewSet, basename="empresa")
router.register("medicos", views.MedicoViewSet, basename="medico")
router.register("trabajadores", views.TrabajadorViewSet, basename="trabajador")
router.register("atenciones", views.AtencionViewSet, basename="atencion")
router.register("citas", views.CitaViewSet, basename="cita")
router.register("profesiogramas", views.ProfesiogramaViewSet, basename="profesiograma")
router.register("pruebas", views.PruebaAtencionViewSet, basename="prueba")
router.register("autorizaciones", views.AutorizacionServicioViewSet, basename="autorizacion")
router.register("me", views.MeView, basename="me")

urlpatterns = router.urls + [
    path("configuracion/", views.ConfiguracionIPSView.as_view(), name="configuracion-ips"),
]
