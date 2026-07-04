from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("historias", views.HistoriaClinicaViewSet, basename="historia")
router.register("conceptos", views.ConceptoViewSet, basename="concepto")

urlpatterns = router.urls
