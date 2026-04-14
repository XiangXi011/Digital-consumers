"""Celery task queue package for async project execution."""

# Import task modules so celery_app.autodiscover_tasks can find them
import backend.tasks.project_tasks  # noqa: F401
import backend.tasks.report_tasks  # noqa: F401
