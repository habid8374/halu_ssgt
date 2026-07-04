from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sedes", views.SedeViewSet, basename="sede")
router.register("consultorios", views.ConsultorioViewSet, basename="consultorio")
router.register("trabajadores", views.TrabajadorViewSet, basename="trabajador")
router.register("atenciones", views.AtencionViewSet, basename="atencion")
router.register("me", views.MeView, basename="me")

urlpatterns = router.urls
