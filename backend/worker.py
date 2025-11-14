"""Celery worker configuration for background tasks."""
from celery import Celery

from backend.config import get_settings

settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    "quran_analysis",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "backend.tasks.tokenization_tasks",
        "backend.tasks.root_extraction_tasks",
        "backend.tasks.backup_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # Results expire after 24 hours
    broker_connection_retry_on_startup=True,
)

# Task routing
celery_app.conf.task_routes = {
    "backend.tasks.tokenization_tasks.*": {"queue": "tokenization"},
    "backend.tasks.root_extraction_tasks.*": {"queue": "root_extraction"},
    "backend.tasks.backup_tasks.*": {"queue": "maintenance"},
}

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "nightly-backup": {
        "task": "backend.tasks.backup_tasks.backup_database",
        "schedule": 86400.0,  # Every 24 hours
        "options": {"queue": "maintenance"},
    },
    "cache-cleanup": {
        "task": "backend.tasks.backup_tasks.cleanup_old_cache",
        "schedule": 3600.0,  # Every hour
        "options": {"queue": "maintenance"},
    },
}
