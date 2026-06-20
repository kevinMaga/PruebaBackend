from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.mixins import AuditDateModel, SoftDeleteQuerySet


class Cliente(AuditDateModel):
    identificacion = models.CharField(
        max_length=20, unique=True, db_index=True,
        help_text="Cédula o RUC del cliente. Ej: 0903369387 / 0992988061001",
    )
    razon_social = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    celular = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.identificacion} - {self.razon_social}"

    def delete_logico(self):
        """Soft delete: nunca se borra físicamente al cliente."""
        self.is_active = False
        self.save(update_fields=["is_active", "modified_at"])


class LineaServicio(AuditDateModel):
    class EstadoLinea(models.TextChoices):
        NO_INSTALADO = "NO_INSTALADO", "No instalado"
        ACTIVO = "ACTIVO", "Activo"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        CANCELADO = "CANCELADO", "Cancelado"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="lineas")
    linea_numero = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    estado_linea = models.CharField(
        max_length=20, choices=EstadoLinea.choices, default=EstadoLinea.NO_INSTALADO,
    )
    fecha_instalacion = models.DateField(blank=True, null=True)
    saldo_vencido = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        ordering = ["cliente_id", "linea_numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "linea_numero"], name="unique_linea_por_cliente",
            )
        ]

    def __str__(self):
        return f"Línea {self.linea_numero} - {self.cliente.razon_social}"

    def clean(self):
        super().clean()
        # Regla: no permitir ACTIVO si el cliente está inactivo
        if self.estado_linea == self.EstadoLinea.ACTIVO and not self.cliente.is_active:
            raise ValidationError(
                {"estado_linea": "No se puede activar la línea: el cliente está inactivo."}
            )
        if self.linea_numero is not None and self.linea_numero < 1:
            raise ValidationError({"linea_numero": "linea_numero debe ser >= 1."})

    def delete_logico(self):
        self.is_active = False
        self.save(update_fields=["is_active", "modified_at"])
