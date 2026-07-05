from rest_framework.routers import DefaultRouter

from .api import FacturaARLViewSet, FacturaViewSet, TarifaViewSet

router = DefaultRouter()
router.register("tarifas", TarifaViewSet, basename="tarifa")
router.register("facturas", FacturaViewSet, basename="factura")
router.register("facturas-arl", FacturaARLViewSet, basename="factura-arl")

urlpatterns = router.urls
