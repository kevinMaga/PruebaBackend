from rest_framework.routers import DefaultRouter

from core.views import ClienteViewSet, LineaServicioViewSet

router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")
router.register(r"lineas", LineaServicioViewSet, basename="lineaservicio")

urlpatterns = router.urls
