from django.urls import path
from rest_framework.routers import DefaultRouter

from billing.views import EstadoCobranzaView, RubroViewSet

router = DefaultRouter()
router.register(r"rubros", RubroViewSet, basename="rubro")

urlpatterns = router.urls + [
    path("lineas/<int:pk>/estado-cobranza/", EstadoCobranzaView.as_view(), name="estado-cobranza"),
]
