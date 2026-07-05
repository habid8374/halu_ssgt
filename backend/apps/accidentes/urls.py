from rest_framework.routers import DefaultRouter

from .api import AccidenteViewSet, AlertaViewSet

router = DefaultRouter()
router.register("accidentes", AccidenteViewSet, basename="accidente")
router.register("alertas", AlertaViewSet, basename="alerta")

urlpatterns = router.urls
