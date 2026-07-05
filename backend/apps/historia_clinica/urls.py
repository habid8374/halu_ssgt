from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .psicosocial import ConsolidadoView, InstrumentoViewSet

router = DefaultRouter()
router.register("historias", views.HistoriaClinicaViewSet, basename="historia")
router.register("conceptos", views.ConceptoViewSet, basename="concepto")
router.register("psicosocial/instrumentos", InstrumentoViewSet, basename="instrumento")

urlpatterns = router.urls + [
    path("psicosocial/consolidado/", ConsolidadoView.as_view(), name="psicosocial-consolidado"),
]
