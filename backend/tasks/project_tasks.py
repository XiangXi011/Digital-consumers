"""Celery tasks for project execution."""

import logging

from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="project.execute_run")
def execute_project_run(self, session_id: str) -> dict:
    """Execute a project research run (planning → dispatch → synthesis).

    Wraps the same logic previously called via BackgroundTasks,
    but now with retry support and Celery state tracking.
    """
    try:
        from backend.api.routers.projects import _execute_project_run

        _execute_project_run(session_id)
        return {"session_id": session_id, "status": "completed"}
    except Exception as exc:
        logger.exception("Celery project execution failed for session_id=%s", session_id)
        try:
            self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            return {"session_id": session_id, "status": "error", "error": str(exc)}
