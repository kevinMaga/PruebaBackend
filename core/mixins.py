from django.db import models


class AuditDateModel(models.Model):
    """Mixin que agrega timestamps de creación/modificación a un modelo."""

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)
