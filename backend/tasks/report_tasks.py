"""Celery tasks for report generation."""

import logging

from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, name="report.generate")
def generate_report(self, session_id: str, report_format: str = "html") -> dict:
    """Generate a report for a completed project session.

    This is a placeholder for future report generation tasks
    that may involve heavy processing (PDF rendering, chart generation, etc.).
    """
    try:
        logger.info(
            "Generating %s report for session_id=%s",
            report_format,
            session_id,
        )
        # Currently report generation is inline with project execution.
        # This task is reserved for future standalone report regeneration.
        return {"session_id": session_id, "format": report_format, "status": "completed"}
    except Exception as exc:
        logger.exception("Report generation failed for session_id=%s", session_id)
        try:
            self.retry(exc=exc, countdown=15)
        except self.MaxRetriesExceededError:
            return {"session_id": session_id, "status": "error", "error": str(exc)}
