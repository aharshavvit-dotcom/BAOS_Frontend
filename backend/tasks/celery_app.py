"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "baos_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.kpi_tasks",
        "tasks.optimizer_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Periodic tasks (beat schedule)
celery_app.conf.beat_schedule = {
    "daily-kpi-calculation": {
        "task": "tasks.kpi_tasks.calculate_daily_kpis",
        "schedule": crontab(hour=0, minute=0),  # Midnight daily
        "args": ("INMAA",),
    },
    "weekly-pattern-refresh": {
        "task": "tasks.kpi_tasks.refresh_patterns",
        "schedule": crontab(hour=2, minute=0, day_of_week="monday"),
        "args": ("INMAA",),
    },
}
