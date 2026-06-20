from rest_framework import serializers

from billing.models import CollectionsRequestLog, Rubro


class RubroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rubro
        fields = [
            "id", "linea_servicio", "valor_total", "estado_rubro",
            "fecha_emision", "fecha_vencimiento", "fecha_pago",
            "created_at", "modified_at",
        ]
        read_only_fields = ["id", "created_at", "modified_at"]

    def validate(self, attrs):
        fecha_emision = attrs.get("fecha_emision", getattr(self.instance, "fecha_emision", None))
        fecha_vencimiento = attrs.get("fecha_vencimiento", getattr(self.instance, "fecha_vencimiento", None))
        if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
            raise serializers.ValidationError(
                {"fecha_vencimiento": "No puede ser anterior a fecha_emision."}
            )
        return attrs


class CollectionsRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionsRequestLog
        fields = [
            "id", "linea_servicio", "started_at", "finished_at", "status",
            "unpaid_count", "action_taken", "error_message", "created_at",
        ]
        read_only_fields = fields


class EstadoCobranzaSerializer(serializers.Serializer):
    linea_id = serializers.IntegerField()
    estado_linea = serializers.CharField()
    saldo_vencido = serializers.DecimalField(max_digits=12, decimal_places=2)
    unpaid_count = serializers.IntegerField()
    ultimos_logs = CollectionsRequestLogSerializer(many=True)
