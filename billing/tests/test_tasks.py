import datetime

import pytest
from django.utils import timezone

from billing.models import CollectionsRequestLog, Rubro
from billing.tasks import run_collections_check
from core.models import Cliente, LineaServicio

pytestmark = pytest.mark.django_db


@pytest.fixture
def linea_activa():
    cliente = Cliente.objects.create(identificacion="0903369387", razon_social="Juan Perez")
    return LineaServicio.objects.create(cliente=cliente, linea_numero=1, estado_linea="ACTIVO")


def test_linea_se_suspende_con_rubro_vencido(linea_activa):
    now = timezone.now()
    Rubro.objects.create(
        linea_servicio=linea_activa,
        valor_total=50,
        estado_rubro="NO_PAGADO",
        fecha_emision=now - datetime.timedelta(days=40),
        fecha_vencimiento=now - datetime.timedelta(days=10),
    )
    run_collections_check()
    linea_activa.refresh_from_db()
    assert linea_activa.estado_linea == "SUSPENDIDO"
    assert linea_activa.saldo_vencido == 50

    log = CollectionsRequestLog.objects.get(linea_servicio=linea_activa)
    assert log.status == "SUCCESS"
    assert log.unpaid_count == 1
    assert log.action_taken == "SUSPEND"


def test_linea_se_reactiva_cuando_ya_no_hay_rubros_vencidos(linea_activa):
    now = timezone.now()
    rubro = Rubro.objects.create(
        linea_servicio=linea_activa,
        valor_total=50,
        estado_rubro="NO_PAGADO",
        fecha_emision=now - datetime.timedelta(days=40),
        fecha_vencimiento=now - datetime.timedelta(days=10),
    )
    run_collections_check()
    linea_activa.refresh_from_db()
    assert linea_activa.estado_linea == "SUSPENDIDO"

    rubro.estado_rubro = "PAGADO"
    rubro.save()
    run_collections_check()
    linea_activa.refresh_from_db()
    assert linea_activa.estado_linea == "ACTIVO"
    assert linea_activa.saldo_vencido == 0


def test_tarea_es_idempotente(linea_activa):
    now = timezone.now()
    Rubro.objects.create(
        linea_servicio=linea_activa,
        valor_total=50,
        estado_rubro="NO_PAGADO",
        fecha_emision=now - datetime.timedelta(days=40),
        fecha_vencimiento=now - datetime.timedelta(days=10),
    )
    run_collections_check()
    run_collections_check()
    linea_activa.refresh_from_db()
    # Tras dos corridas seguidas sin cambios en los rubros, el estado se mantiene estable
    assert linea_activa.estado_linea == "SUSPENDIDO"
    assert linea_activa.saldo_vencido == 50
    assert CollectionsRequestLog.objects.filter(linea_servicio=linea_activa).count() == 2


def test_no_suspende_lineas_canceladas(linea_activa):
    linea_activa.estado_linea = "CANCELADO"
    linea_activa.save()
    now = timezone.now()
    Rubro.objects.create(
        linea_servicio=linea_activa,
        valor_total=50,
        estado_rubro="NO_PAGADO",
        fecha_emision=now - datetime.timedelta(days=40),
        fecha_vencimiento=now - datetime.timedelta(days=10),
    )
    run_collections_check()
    linea_activa.refresh_from_db()
    # Regla de negocio: CANCELADO/NO_INSTALADO no cambian de estado automáticamente
    assert linea_activa.estado_linea == "CANCELADO"


def test_rubro_no_vencido_no_afecta_saldo(linea_activa):
    now = timezone.now()
    Rubro.objects.create(
        linea_servicio=linea_activa,
        valor_total=50,
        estado_rubro="NO_PAGADO",
        fecha_emision=now,
        fecha_vencimiento=now + datetime.timedelta(days=10),  # aún no vence
    )
    run_collections_check()
    linea_activa.refresh_from_db()
    assert linea_activa.estado_linea == "ACTIVO"
    assert linea_activa.saldo_vencido == 0
