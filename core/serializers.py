from rest_framework import serializers

from core.models import Cliente, LineaServicio


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            "id", "identificacion", "razon_social", "email", "celular",
            "is_active", "created_at", "modified_at",
        ]
        read_only_fields = ["id", "created_at", "modified_at"]

    def validate_identificacion(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("La identificación no puede estar vacía.")
        return value.strip()


class LineaServicioSerializer(serializers.ModelSerializer):
    cliente_identificacion = serializers.CharField(source="cliente.identificacion", read_only=True)

    class Meta:
        model = LineaServicio
        fields = [
            "id", "cliente", "cliente_identificacion", "linea_numero", "estado_linea",
            "fecha_instalacion", "saldo_vencido", "is_active", "created_at", "modified_at",
        ]
        read_only_fields = ["id", "saldo_vencido", "created_at", "modified_at"]

    def validate(self, attrs):
        # Tomamos el cliente y estado, ya sea del payload o de la instancia existente (PATCH)
        cliente = attrs.get("cliente", getattr(self.instance, "cliente", None))
        estado_linea = attrs.get("estado_linea", getattr(self.instance, "estado_linea", None))
        linea_numero = attrs.get("linea_numero", getattr(self.instance, "linea_numero", None))

        if linea_numero is not None and linea_numero < 1:
            raise serializers.ValidationError({"linea_numero": "Debe ser >= 1."})

        if estado_linea == LineaServicio.EstadoLinea.ACTIVO and cliente and not cliente.is_active:
            raise serializers.ValidationError(
                {"estado_linea": "No se puede activar la línea: el cliente está inactivo."}
            )

        # Validación de unicidad cliente + linea_numero (a nivel de serializer, mensaje claro)
        qs = LineaServicio.objects.filter(cliente=cliente, linea_numero=linea_numero)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if cliente and linea_numero and qs.exists():
            raise serializers.ValidationError(
                {"linea_numero": "Este cliente ya tiene una línea con ese número."}
            )

        return attrs
