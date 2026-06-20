from django.contrib import admin

from billing.models import CollectionsRequestLog, Rubro


@admin.register(Rubro)
class RubroAdmin(admin.ModelAdmin):
    list_display = ("id", "linea_servicio", "valor_total", "estado_rubro", "fecha_vencimiento")
    list_filter = ("estado_rubro",)


@admin.register(CollectionsRequestLog)
class CollectionsRequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "linea_servicio", "status", "unpaid_count", "action_taken", "started_at")
    list_filter = ("status", "action_taken")
