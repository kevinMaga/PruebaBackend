import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("isp_backend")

# Carga la config de Celery desde settings.py (prefijo CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodescubre tasks.py en cada app instalada
app.autodiscover_tasks()

# Tarea periódica cada 5 minutos: control de morosidad
app.conf.beat_schedule = {
    "run-collections-check-every-5-minutes": {
        "task": "billing.tasks.run_collections_check",
        "schedule": crontab(minute="*/5"),
    },
}
