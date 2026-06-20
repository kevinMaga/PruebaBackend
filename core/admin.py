from django.contrib import admin

from core.models import Cliente, LineaServicio


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id", "identificacion", "razon_social", "is_active", "created_at")
    search_fields = ("identificacion", "razon_social")
    list_filter = ("is_active",)


@admin.register(LineaServicio)
class LineaServicioAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "linea_numero", "estado_linea", "saldo_vencido", "is_active")
    list_filter = ("estado_linea", "is_active")
    search_fields = ("cliente__identificacion", "cliente__razon_social")
