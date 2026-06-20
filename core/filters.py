import django_filters

from core.models import Cliente, LineaServicio


class ClienteFilter(django_filters.FilterSet):
    identificacion = django_filters.CharFilter(lookup_expr="icontains")
    razon_social = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Cliente
        fields = ["identificacion", "razon_social"]


class LineaServicioFilter(django_filters.FilterSet):
    cliente_id = django_filters.NumberFilter(field_name="cliente_id")
    estado_linea = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = LineaServicio
        fields = ["cliente_id", "estado_linea"]
