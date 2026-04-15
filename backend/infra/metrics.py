"""Business metrics definitions for the market research platform.

Defines counters, histograms, and gauges used across the application.
All metrics gracefully degrade to no-ops if OpenTelemetry is unavailable.
"""

from typing import Optional

from backend.infra.otel_config import get_meter

# Module-level metric instruments (initialized lazily)
_projects_created: Optional[object] = None
_pipeline_duration: Optional[object] = None
_persona_eval_duration: Optional[object] = None
_llm_call_duration: Optional[object] = None
_llm_call_errors: Optional[object] = None
_repeated_phrase_rate: Optional[object] = None
_minority_survival_rate: Optional[object] = None


def _ensure_metrics():
    """Lazily initialize metric instruments on first use."""
    global _projects_created, _pipeline_duration, _persona_eval_duration
    global _llm_call_duration, _llm_call_errors, _repeated_phrase_rate, _minority_survival_rate

    if _projects_created is not None:
        return

    meter = get_meter()
    if meter is None:
        return

    _projects_created = meter.create_counter(
        name="projects_created_total",
        description="Total number of projects created",
        unit="1",
    )
    _pipeline_duration = meter.create_histogram(
        name="pipeline_duration_seconds",
        description="End-to-end research pipeline duration",
        unit="s",
    )
    _persona_eval_duration = meter.create_histogram(
        name="persona_evaluation_duration_seconds",
        description="Single persona evaluation duration",
        unit="s",
    )
    _llm_call_duration = meter.create_histogram(
        name="llm_call_duration_seconds",
        description="LLM API call duration",
        unit="s",
    )
    _llm_call_errors = meter.create_counter(
        name="llm_call_errors_total",
        description="Total LLM call errors",
        unit="1",
    )
    _repeated_phrase_rate = meter.create_gauge(
        name="repeated_phrase_rate",
        description="Repeated phrase rate in persona outputs (quality gate: >0.5 = alert)",
        unit="1",
    )
    _minority_survival_rate = meter.create_gauge(
        name="minority_survival_rate",
        description="Minority opinion survival rate (quality gate: <0.3 = alert)",
        unit="1",
    )


def record_project_created():
    _ensure_metrics()
    if _projects_created:
        _projects_created.add(1)


def record_pipeline_duration(seconds: float):
    _ensure_metrics()
    if _pipeline_duration:
        _pipeline_duration.record(seconds)


def record_persona_eval_duration(seconds: float):
    _ensure_metrics()
    if _persona_eval_duration:
        _persona_eval_duration.record(seconds)


def record_llm_call(duration_seconds: float, success: bool = True):
    _ensure_metrics()
    if _llm_call_duration:
        _llm_call_duration.record(duration_seconds)
    if not success and _llm_call_errors:
        _llm_call_errors.add(1)


def record_quality_gates(repeated_phrase_rate: float, minority_survival_rate: float):
    _ensure_metrics()
    if _repeated_phrase_rate:
        _repeated_phrase_rate.set(repeated_phrase_rate)
    if _minority_survival_rate:
        _minority_survival_rate.set(minority_survival_rate)
