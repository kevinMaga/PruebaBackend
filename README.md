# ISP Backend — Gestión de Clientes, Líneas y Cobranza

🎥 **Video demostrativo**: https://drive.google.com/file/d/1Kz0IJl-JXn8mkzuCrc9_AfDdi4i-2wqn/view?usp=drive_link

Mini-servicio REST (Django + DRF) con proceso asíncrono y periódico (Celery + Celery Beat)
de control de morosidad sobre líneas de servicio.

## Stack

- Django 5 + DRF
- PostgreSQL (Docker) / SQLite (pruebas locales rápidas)
- Celery + Celery Beat (con `django-celery-beat` como scheduler persistido en BD)
- Redis como broker
- Docker / docker-compose

## Estructura del proyecto

```
isp_backend/
├── config/          # settings, celery.py, urls, exception handler
├── core/            # Cliente, LineaServicio (Etapa 1)
├── billing/         # Rubro, CollectionsRequestLog, tasks.py (Etapa 2)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 1. Levantar el proyecto con Docker (recomendado)

```bash
cp .env.example .env
# .env ya viene configurado con DB_ENGINE=postgres apuntando al servicio "db" del compose

docker compose build
docker compose up -d        # levanta db, redis, web, celery_worker, celery_beat
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser   # opcional, para /admin
```

La API queda disponible en `http://localhost:8000/api/`.

Para ver logs de la tarea periódica:

```bash
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```

## 2. Levantar el proyecto en local (sin Docker, con SQLite)

Útil para desarrollo rápido o si no quieres correr Postgres.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Cambia en .env: DB_ENGINE=sqlite

python manage.py migrate
python manage.py runserver
```

Para correr Celery en local necesitas Redis corriendo en `localhost:6379` (puedes levantarlo
suelto con `docker run -p 6379:6379 redis:7-alpine`) y en otras dos terminales:

```bash
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 3. Variables de entorno (`.env`)

| Variable | Descripción | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | dev key |
| `DJANGO_DEBUG` | Modo debug | True |
| `DB_ENGINE` | `postgres` o `sqlite` | sqlite |
| `DB_NAME/USER/PASSWORD/HOST/PORT` | Conexión a Postgres | — |
| `REDIS_URL` | Broker/backend de Celery | redis://localhost:6379/0 |

---

## 4. Endpoints principales

### Clientes
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/clientes/` | Listar (filtros `?identificacion=` `?razon_social=`) |
| POST | `/api/clientes/` | Crear |
| GET | `/api/clientes/{id}/` | Detalle |
| PATCH | `/api/clientes/{id}/` | Actualización parcial |
| DELETE | `/api/clientes/{id}/` | Eliminación lógica (`is_active=False`) |

### Líneas de servicio
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/lineas/` | Listar (filtros `?cliente_id=` `?estado_linea=`) |
| POST | `/api/lineas/` | Crear |
| GET | `/api/lineas/{id}/` | Detalle |
| PATCH | `/api/lineas/{id}/` | Actualización parcial |
| DELETE | `/api/lineas/{id}/` | Eliminación lógica |
| GET | `/api/lineas/{id}/estado-cobranza/` | **Bonus**: resumen de cobranza (unpaid_count, saldo_vencido, últimos 5 logs) |

### Rubros
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/rubros/` | Listar/crear cargos |
| GET/PATCH/DELETE | `/api/rubros/{id}/` | Detalle/editar/borrar |

### Otros
- `GET /api/health/` — healthcheck simple.
- `/admin/` — Django admin (gestión visual de logs, rubros, periodic tasks de Beat).

### Ejemplo de uso

```bash
# Crear cliente
curl -X POST http://localhost:8000/api/clientes/ \
  -H "Content-Type: application/json" \
  -d '{"identificacion":"0903369387","razon_social":"Juan Perez","email":"juan@test.com"}'

# Crear línea
curl -X POST http://localhost:8000/api/lineas/ \
  -H "Content-Type: application/json" \
  -d '{"cliente":1,"linea_numero":1,"estado_linea":"ACTIVO"}'

# Crear rubro vencido (para forzar morosidad)
curl -X POST http://localhost:8000/api/rubros/ \
  -H "Content-Type: application/json" \
  -d '{"linea_servicio":1,"valor_total":50,"estado_rubro":"NO_PAGADO","fecha_emision":"2026-05-01T00:00:00Z","fecha_vencimiento":"2026-06-01T00:00:00Z"}'

# Ver resumen de cobranza
curl http://localhost:8000/api/lineas/1/estado-cobranza/
```

---

## 5. Tarea periódica de morosidad (Etapa 2)

`billing.tasks.run_collections_check` corre cada 5 minutos vía Celery Beat
(`config/celery.py`, `crontab(minute="*/5")`).

**Por cada línea activa:**
1. Calcula rubros `NO_PAGADO` con `fecha_vencimiento < now()`.
2. Actualiza `saldo_vencido` (suma de esos rubros).
3. Si tiene rubros vencidos → `estado_linea = SUSPENDIDO`, `action_taken = SUSPEND`.
4. Si ya no tiene rubros vencidos y estaba `SUSPENDIDO` → vuelve a `ACTIVO`, `action_taken = UNSUSPEND`.
5. Guarda un `CollectionsRequestLog` (SUCCESS/FAILED) con timestamps, `unpaid_count` y `error_message` si aplica.

**Regla de negocio documentada**: líneas en `CANCELADO` o `NO_INSTALADO` **nunca** cambian de
estado automáticamente por esta tarea, aunque tengan rubros vencidos (su `saldo_vencido` sí se
actualiza, de forma informativa).

### Probar la tarea manualmente (sin esperar los 5 minutos)

```bash
docker compose exec web python manage.py shell -c "from billing.tasks import run_collections_check; run_collections_check()"
```

O dispararla async vía Celery (requiere worker corriendo):

```python
from billing.tasks import run_collections_check
run_collections_check.delay()
```

---

## 6. Decisiones de diseño y trade-offs

- **Soft delete**: `Cliente` y `LineaServicio` nunca se borran físicamente; el `DELETE` del
  API solo cambia `is_active=False`. Por eso las FKs hacia ellos usan `on_delete=PROTECT`
  (Rubro → LineaServicio, CollectionsRequestLog → LineaServicio): así nunca se puede borrar
  en cascada información de cobranza/auditoría.
- **Idempotencia de la tarea**: la tarea recalcula `saldo_vencido` y el estado desde cero en
  cada corrida (no acumula), así que correrla N veces seguidas sin cambios en los rubros
  produce el mismo resultado en `LineaServicio`. Lo único que crece son los logs de auditoría
  (esperado: cada corrida es una ejecución real y debe quedar trazada).
- **Evitar N+1**: en lugar de iterar línea por línea consultando sus rubros, se hace **una sola
  query agregada** (`values("linea_servicio_id").annotate(Count, Sum)`) para todas las líneas
  activas, y luego se persiste todo con `bulk_update` + `bulk_create` dentro de una transacción.
- **Resiliencia**: el `try/except` está dentro del loop por línea — si una línea falla
  (por ejemplo, un error de datos), no se detiene el procesamiento de las demás; se registra
  un log `FAILED` con `error_message` y se continúa. La tarea además tiene `max_retries=2` a
  nivel de Celery para reintentar la ejecución completa ante errores de infraestructura
  (broker, DB caída momentáneamente).
- **CANCELADO/NO_INSTALADO exentos de suspensión automática**: se asume que una línea cancelada
  ya no presta servicio (no tiene sentido "suspenderla" otra vez) y una no instalada todavía no
  debería tener rubros vencidos relevantes para corte de servicio. Esto queda como `ESTADOS_EXENTOS`
  en `billing/tasks.py`, fácilmente ajustable si la regla de negocio real es otra.
- **Validación de "no activar línea con cliente inactivo"**: se implementó tanto a nivel de
  modelo (`clean()`) como de serializer (mensaje de error más claro y temprano sin necesitar
  llamar a `full_clean()` manualmente desde la vista).
- **Manejo de excepciones uniforme**: se usa un `EXCEPTION_HANDLER` custom en DRF
  (`config/exceptions.py`) que envuelve todos los errores (400/404/409/500) en un formato
  consistente `{"error": true, "detail": ..., "code": ...}`.

## 7. Tests

```bash
DB_ENGINE=sqlite python -m pytest -v
```

Cubre: validaciones de modelo (unicidad, soft delete, regla cliente inactivo), endpoints CRUD
(creación, filtros, eliminación lógica, errores 400), y la tarea de morosidad (suspensión,
reactivación, idempotencia, exención de CANCELADO, rubros aún no vencidos).

## 8. Pendiente / posibles mejoras futuras

- Autenticación Token/JWT real con permisos (solo admin puede `DELETE`) — actualmente
  `AllowAny` para simplificar las pruebas de la evaluación.
- Métricas (Prometheus) y un endpoint `/api/health/` más completo (chequeo de DB/Redis).
- Paginación cursor-based si el volumen de líneas/rubros crece mucho.
