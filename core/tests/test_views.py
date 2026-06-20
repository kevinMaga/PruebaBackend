import pytest
from rest_framework.test import APIClient

from core.models import Cliente, LineaServicio

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_crear_cliente_endpoint(client):
    resp = client.post(
        "/api/clientes/",
        {"identificacion": "0903369387", "razon_social": "Juan Perez"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["identificacion"] == "0903369387"


def test_crear_cliente_duplicado_devuelve_409_o_400(client):
    Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    resp = client.post(
        "/api/clientes/",
        {"identificacion": "0903369387", "razon_social": "Otro"},
        format="json",
    )
    assert resp.status_code in (400, 409)


def test_eliminar_cliente_es_logico(client):
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    resp = client.delete(f"/api/clientes/{cliente.id}/")
    assert resp.status_code == 200
    cliente.refresh_from_db()
    assert cliente.is_active is False


def test_listar_clientes_filtro_identificacion(client):
    Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    Cliente.objects.create(identificacion="0992988061001", razon_social="Empresa SA")
    resp = client.get("/api/clientes/?identificacion=0903369387")
    assert resp.status_code == 200
    assert resp.data["count"] == 1


def test_crear_linea_servicio(client):
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    resp = client.post(
        "/api/lineas/",
        {"cliente": cliente.id, "linea_numero": 1, "estado_linea": "ACTIVO"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["saldo_vencido"] == "0.00"


def test_crear_linea_duplicada_devuelve_400(client):
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    LineaServicio.objects.create(cliente=cliente, linea_numero=1)
    resp = client.post(
        "/api/lineas/",
        {"cliente": cliente.id, "linea_numero": 1, "estado_linea": "ACTIVO"},
        format="json",
    )
    assert resp.status_code == 400


def test_no_activar_linea_con_cliente_inactivo(client):
    cliente = Cliente.objects.create(
        identificacion="0903369387", razon_social="Juan Perez", is_active=False
    )
    resp = client.post(
        "/api/lineas/",
        {"cliente": cliente.id, "linea_numero": 1, "estado_linea": "ACTIVO"},
        format="json",
    )
    assert resp.status_code == 400
