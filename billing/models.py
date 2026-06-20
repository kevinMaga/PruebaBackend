from django.db import models

from core.mixins import AuditDateModel
from core.models import LineaServicio


class Rubro(AuditDateModel):
    class EstadoRubro(models.TextChoices):
        NO_PAGADO = "NO_PAGADO", "No pagado"
        PAGADO = "PAGADO", "Pagado"
        VENCIDO = "VENCIDO", "Vencido"
        ANULADO = "ANULADO", "Anulado"

    linea_servicio = models.ForeignKey(
        LineaServicio, on_delete=models.PROTECT, related_name="rubros"
    )
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    estado_rubro = models.CharField(
        max_length=20, choices=EstadoRubro.choices, default=EstadoRubro.NO_PAGADO
    )
    fecha_emision = models.DateTimeField()
    fecha_vencimiento = models.DateTimeField()
    fecha_pago = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_vencimiento"]
        indexes = [
            models.Index(fields=["estado_rubro", "fecha_vencimiento"]),
        ]

    def __str__(self):
        return f"Rubro {self.id} - Línea {self.linea_servicio_id} - {self.estado_rubro}"


class CollectionsRequestLog(AuditDateModel):
    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    class ActionTaken(models.TextChoices):
        NONE = "NONE", "None"
        SUSPEND = "SUSPEND", "Suspend"
        UNSUSPEND = "UNSUSPEND", "Unsuspend"

    linea_servicio = models.ForeignKey(
        LineaServicio, on_delete=models.PROTECT, related_name="collections_logs"
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    unpaid_count = models.PositiveSmallIntegerField(default=0)
    action_taken = models.CharField(
        max_length=10, choices=ActionTaken.choices, default=ActionTaken.NONE
    )
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Log {self.id} - Línea {self.linea_servicio_id} - {self.status}"
