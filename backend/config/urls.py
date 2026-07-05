from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.usuarios.jwt_views import TenantTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TenantTokenObtainPairView.as_view(), name="token_obtain"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.atenciones.urls")),
    path("api/", include("apps.historia_clinica.urls")),
    path("api/", include("apps.accidentes.urls")),
]
