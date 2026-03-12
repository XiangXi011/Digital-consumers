from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


class AnalysisGraphState(TypedDict, total=False):
    research_input: Any
    report: Dict[str, Any]
    html: str
    error: str


class DingTalkWorkflowState(TypedDict, total=False):
    event: Dict[str, Any]
    task_id: str
    session: Any
    status: str
    reset_requested: bool
    reset_completed: bool
    explicit_run_requested: bool
    allow_assumption_run: bool
    has_minimum_runnable_info: bool
    missing_fields: List[str]
    research_plan: Dict[str, Any]
    planner_requires_clarification: bool
    response: Dict[str, Any]
    research_input_payload: Dict[str, Any]
    research_input: Any
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
