"""
Celery async task queue for background jobs:
  - drift_scan        → runs PSI drift analysis every 6h
  - analytics_refresh → refreshes aggregated analytics tables every 1h
  - model_health      → pings inference health every 15min

production_equivalent: Replace with Apache Airflow DAGs or AWS Step Functions
for dependency management, retries, and SLA alerting.
"""

from celery import Celery
from celery.schedules import crontab
from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "fraudstream",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery_app.conf.beat_schedule = {
    "drift-scan-every-6h": {
        "task": "app.tasks.run_drift_scan",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "analytics-refresh-every-1h": {
        "task": "app.tasks.refresh_analytics",
        "schedule": crontab(minute=0),
    },
    "model-health-check-every-15min": {
        "task": "app.tasks.model_health_check",
        "schedule": crontab(minute="*/15"),
    },
}
