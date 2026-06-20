import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from core.models import Cliente, LineaServicio

pytestmark = pytest.mark.django_db


def test_crear_cliente():
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    assert cliente.is_active is True
    assert str(cliente) == "0903369387 - Juan Perez"


def test_identificacion_unica():
    Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    with pytest.raises(IntegrityError):
        Cliente.objects.create(identificacion="0903369387", razon_social="Otro")


def test_soft_delete_cliente():
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    cliente.delete_logico()
    cliente.refresh_from_db()
    assert cliente.is_active is False
    assert Cliente.objects.filter(pk=cliente.pk).exists()  # no se borró físicamente


def test_no_se_puede_activar_linea_si_cliente_inactivo():
    cliente = Cliente.objects.create(
        identificacion="0903369387", razon_social="Juan Perez", is_active=False
    )
    linea = LineaServicio(cliente=cliente, linea_numero=1, estado_linea="ACTIVO")
    with pytest.raises(ValidationError):
        linea.clean()


def test_unique_together_cliente_linea_numero():
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    LineaServicio.objects.create(cliente=cliente, linea_numero=1)
    with pytest.raises(IntegrityError):
        LineaServicio.objects.create(cliente=cliente, linea_numero=1)
