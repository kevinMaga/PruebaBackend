from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.response import Response

from core.filters import ClienteFilter, LineaServicioFilter
from core.models import Cliente, LineaServicio
from core.serializers import ClienteSerializer, LineaServicioSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    """
    CRUD de Clientes. El DELETE es lógico (is_active=False), nunca borra físicamente.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    filterset_class = ClienteFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_logico()
        return Response(
            {"detail": "Cliente desactivado (eliminación lógica)."},
            status=status.HTTP_200_OK,
        )


class LineaServicioViewSet(viewsets.ModelViewSet):
    """
    CRUD de Líneas de Servicio. El DELETE es lógico (is_active=False).
    """
    queryset = LineaServicio.objects.select_related("cliente").all()
    serializer_class = LineaServicioSerializer
    filterset_class = LineaServicioFilter

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean(exclude=["saldo_vencido"])
        except DjangoValidationError as exc:
            instance.delete()
            raise

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_logico()
        return Response(
            {"detail": "Línea desactivada (eliminación lógica)."},
            status=status.HTTP_200_OK,
        )
