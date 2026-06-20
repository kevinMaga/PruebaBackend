from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import CollectionsRequestLog, Rubro
from billing.serializers import EstadoCobranzaSerializer, RubroSerializer
from core.models import LineaServicio


class RubroViewSet(viewsets.ModelViewSet):
    """CRUD simple de Rubros (cargos), usado para detectar morosidad."""
    queryset = Rubro.objects.select_related("linea_servicio").all()
    serializer_class = RubroSerializer
    filterset_fields = ["linea_servicio", "estado_rubro"]


class EstadoCobranzaView(APIView):
    """
    GET /api/lineas/{id}/estado-cobranza/
    Endpoint bonus: resumen de cobranza de una línea (unpaid_count, saldo_vencido,
    últimos logs de ejecución del proceso de morosidad).
    """

    def get(self, request, pk=None):
        linea = get_object_or_404(LineaServicio, pk=pk)
        now = timezone.now()
        unpaid_count = Rubro.objects.filter(
            linea_servicio=linea,
            estado_rubro=Rubro.EstadoRubro.NO_PAGADO,
            fecha_vencimiento__lt=now,
        ).count()
        ultimos_logs = CollectionsRequestLog.objects.filter(
            linea_servicio=linea
        ).order_by("-started_at")[:5]

        data = {
            "linea_id": linea.id,
            "estado_linea": linea.estado_linea,
            "saldo_vencido": linea.saldo_vencido,
            "unpaid_count": unpaid_count,
            "ultimos_logs": ultimos_logs,
        }
        serializer = EstadoCobranzaSerializer(data)
        return Response(serializer.data)
