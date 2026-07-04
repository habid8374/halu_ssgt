"""
URLs raíz. Las rutas de API por dominio se montan en el paso posterior
(vistas + permisos DRF). Aquí queda el admin y el esqueleto de /api/.
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("api/", include("apps.atenciones.urls")),  # tras aprobar modelos
]
