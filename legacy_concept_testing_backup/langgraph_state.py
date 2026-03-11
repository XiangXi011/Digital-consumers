from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


class AnalysisGraphState(TypedDict, total=False):
    concept_input: Any
    product: Any
    evaluation_results: List[Dict[str, Any]]
    discussion_participants: List[str]
    deep_dive_candidates: Dict[str, List[str]]
    discussion: Dict[str, Any]
    deep_dives: Dict[str, List[Dict[str, Any]]]
    orchestrator_report: Dict[str, Any]
    report: Dict[str, Any]
    markdown: str
    error: str


class DingTalkWorkflowState(TypedDict, total=False):
    event: Dict[str, Any]
    task_id: str
    session: Any
    status: str
    reset_requested: bool
    reset_completed: bool
    explicit_run_requested: bool
    has_minimum_runnable_info: bool
    missing_fields: List[str]
    response: Dict[str, Any]
    concept_payload: Dict[str, Any]
    concept_input: Any
    report: Dict[str, Any]
    html: str
    html_report_path: str
    json_report_path: str
    public_report_url: str
    error: str


def stringify_path(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    return str(path)
