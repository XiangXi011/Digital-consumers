"""Celery application configuration.

Usage:
    # Start worker
    celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=4

    # Start beat scheduler (if needed)
    celery -A backend.tasks.celery_app beat --loglevel=info
"""

import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "market_agent",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
    task_max_retries=3,
    result_expires=3600,
    beat_schedule={},
)

# Auto-discover tasks in sibling modules
celery_app.autodiscover_tasks(["backend.tasks"])
