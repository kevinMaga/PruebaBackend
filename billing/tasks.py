import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from billing.models import CollectionsRequestLog, Rubro
from core.models import LineaServicio

logger = logging.getLogger("billing")

# Estados de línea sobre los cuales NUNCA se aplica suspensión/reactivación automática,
# aunque tengan rubros vencidos. Regla de negocio documentada en el README.
ESTADOS_EXENTOS = {LineaServicio.EstadoLinea.CANCELADO, LineaServicio.EstadoLinea.NO_INSTALADO}


@shared_task(name="billing.tasks.run_collections_check", bind=True, max_retries=2, default_retry_delay=30)
def run_collections_check(self):
    """
    Tarea periódica (cada 5 min vía Celery Beat) que:
      1. Recorre todas las líneas activas (is_active=True).
      2. Calcula rubros NO_PAGADO con fecha_vencimiento < now() por línea (sin N+1: una sola
         query agregada para todas las líneas).
      3. Actualiza saldo_vencido de la línea.
      4. Suspende la línea si tiene rubros vencidos, o la reactiva si ya no tiene y estaba
         SUSPENDIDO. CANCELADO/NO_INSTALADO se documentan como exentos de este cambio
         automático de estado, aunque sí se actualiza su saldo_vencido informativo.
      5. Deja un log (CollectionsRequestLog) por línea, SUCCESS o FAILED.

    Idempotencia: si la tarea corre dos veces seguidas sin cambios en los rubros, el
    resultado (saldo_vencido, estado_linea) es el mismo en ambas corridas; solo se generan
    nuevos logs de auditoría (esperado), pero no se duplican ni acumulan cambios de estado.
    """
    now = timezone.now()
    lineas = LineaServicio.objects.filter(is_active=True).select_related("cliente")

    # Una sola query agregada para evitar N+1: cuenta y suma de rubros vencidos por línea.
    agregados = (
        Rubro.objects.filter(
            estado_rubro=Rubro.EstadoRubro.NO_PAGADO,
            fecha_vencimiento__lt=now,
            linea_servicio__in=lineas,
        )
        .values("linea_servicio_id")
        .annotate(unpaid_count=Count("id"), total_vencido=Sum("valor_total"))
    )
    agregados_por_linea = {
        row["linea_servicio_id"]: row for row in agregados
    }

    logs_a_crear = []
    lineas_a_actualizar = []
    procesadas = 0
    fallidas = 0

    for linea in lineas:
        started_at = timezone.now()
        try:
            data = agregados_por_linea.get(linea.id)
            unpaid_count = data["unpaid_count"] if data else 0
            total_vencido = data["total_vencido"] if data else Decimal("0")

            nuevo_saldo = total_vencido or Decimal("0")
            action_taken = CollectionsRequestLog.ActionTaken.NONE

            cambios_estado_permitidos = linea.estado_linea not in ESTADOS_EXENTOS

            if cambios_estado_permitidos:
                if unpaid_count > 0 and linea.estado_linea != LineaServicio.EstadoLinea.SUSPENDIDO:
                    linea.estado_linea = LineaServicio.EstadoLinea.SUSPENDIDO
                    action_taken = CollectionsRequestLog.ActionTaken.SUSPEND
                elif unpaid_count == 0 and linea.estado_linea == LineaServicio.EstadoLinea.SUSPENDIDO:
                    linea.estado_linea = LineaServicio.EstadoLinea.ACTIVO
                    action_taken = CollectionsRequestLog.ActionTaken.UNSUSPEND

            # Idempotencia: solo se marca "cambio" real si el valor difiere del actual.
            if linea.saldo_vencido != nuevo_saldo:
                linea.saldo_vencido = nuevo_saldo

            # auto_now no se dispara en bulk_update, se setea manualmente.
            linea.modified_at = timezone.now()
            lineas_a_actualizar.append(linea)

            logs_a_crear.append(
                CollectionsRequestLog(
                    linea_servicio=linea,
                    started_at=started_at,
                    finished_at=timezone.now(),
                    status=CollectionsRequestLog.Status.SUCCESS,
                    unpaid_count=unpaid_count,
                    action_taken=action_taken,
                )
            )
            procesadas += 1

        except Exception as exc:  # resiliencia: una línea con error no detiene el resto
            fallidas += 1
            logger.exception("Error procesando línea %s en control de morosidad", linea.id)
            logs_a_crear.append(
                CollectionsRequestLog(
                    linea_servicio=linea,
                    started_at=started_at,
                    finished_at=timezone.now(),
                    status=CollectionsRequestLog.Status.FAILED,
                    unpaid_count=0,
                    action_taken=CollectionsRequestLog.ActionTaken.NONE,
                    error_message=str(exc),
                )
            )

    # Persistencia en una sola transacción: bulk_update + bulk_create (evita N+1 al guardar).
    with transaction.atomic():
        if lineas_a_actualizar:
            LineaServicio.objects.bulk_update(
                lineas_a_actualizar, ["estado_linea", "saldo_vencido", "modified_at"]
            )
        if logs_a_crear:
            CollectionsRequestLog.objects.bulk_create(logs_a_crear)

    logger.info(
        "Control de morosidad finalizado: %s líneas procesadas, %s fallidas.",
        procesadas, fallidas,
    )
    return {"procesadas": procesadas, "fallidas": fallidas}
