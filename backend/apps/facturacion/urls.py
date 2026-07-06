from rest_framework.routers import DefaultRouter

from .api import FacturaARLViewSet, FacturaViewSet, GlosaViewSet, TarifaViewSet

router = DefaultRouter()
router.register("tarifas", TarifaViewSet, basename="tarifa")
router.register("facturas", FacturaViewSet, basename="factura")
router.register("facturas-arl", FacturaARLViewSet, basename="factura-arl")
router.register("glosas", GlosaViewSet, basename="glosa")

urlpatterns = router.urls
