"""Dashboard statistics API."""

import json
import structlog
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.paths import DINGTALK_REPORTS_DIR, DINGTALK_SESSIONS_DIR, OUTPUTS_DIR

logger = structlog.get_logger(__name__)

router = APIRouter()


class DashboardStats(BaseModel):
    total_reports: int = 0
    weekly_reviews: int = 0
    total_projects: int = 0
    avg_completion_hours: float = 0.0
    recent_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    status_distribution: Dict[str, int] = Field(default_factory=dict)


def _is_valid_report_file(path: Path) -> bool:
    name = path.stem.lower()
    if not name or name.startswith("."):
        return False
    excluded_keywords = [
        "debug",
        "sample",
        "consistency_check",
        "diversity_check",
        "persona_constraint",
        "persona_report",
        "simulation_report",
    ]
    return not any(key in name for key in excluded_keywords)


def _avg_completion_hours_from_sessions(sessions: List[tuple[Any, Dict[str, Any]]]) -> float:
    durations: List[float] = []
    for session_path, data in sessions:
        if str(data.get("status", "")) != "completed":
            continue

        report_path_raw = data.get("json_report_path") or data.get("html_report_path")
        if not report_path_raw:
            continue

        report_path = Path(str(report_path_raw))
        if not report_path.exists():
            continue

        try:
            created_ts = session_path.stat().st_ctime
            completed_ts = report_path.stat().st_mtime
        except Exception:
            continue

        delta_hours = (completed_ts - created_ts) / 3600.0
        if delta_hours <= 0:
            continue
        if delta_hours > 24 * 14:
            continue
        durations.append(delta_hours)

    if not durations:
        return 0.0
    return round(sum(durations) / len(durations), 2)


@router.get("/stats/dashboard", response_model=DashboardStats)
def get_dashboard_stats(user=Depends(get_current_user)):
    report_count = 0
    for scan_dir in [OUTPUTS_DIR, DINGTALK_REPORTS_DIR]:
        if scan_dir.exists():
            report_count += len([path for path in scan_dir.glob("*.json") if _is_valid_report_file(path)])

    sessions: List[tuple[Any, Dict[str, Any]]] = []
    status_dist: Dict[str, int] = {}
    if DINGTALK_SESSIONS_DIR.exists():
        for path in sorted(DINGTALK_SESSIONS_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            status = str(data.get("status", "unknown") or "unknown")
            status_dist[status] = status_dist.get(status, 0) + 1
            sessions.append((path, data))

    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_reviews = 0
    for path, _ in sessions:
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) >= week_start:
                weekly_reviews += 1
        except Exception:
            continue

    recent_tasks: List[Dict[str, Any]] = []
    for path, data in sessions[:5]:
        fields = data.get("fields", {})
        user_question = fields.get("user_question", {})
        name = ""
        if isinstance(user_question, dict):
            name = str(user_question.get("value", "") or "").strip()
        if not name:
            name = data.get("session_id", path.stem)[:30]

        product = fields.get("product_info", {})
        product_name = ""
        if isinstance(product, dict):
            product_name = str(product.get("value", "") or "").strip()[:30]

        recent_tasks.append(
            {
                "session_id": data.get("session_id", path.stem),
                "name": name,
                "product": product_name,
                "status": data.get("status", "collecting"),
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "status_updated_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "project_type_raw": (fields.get("question_type", {}) or {}).get("value", "") if isinstance(fields, dict) else "",
            }
        )

    return DashboardStats(
        total_reports=report_count,
        weekly_reviews=weekly_reviews,
        total_projects=len(sessions),
        avg_completion_hours=_avg_completion_hours_from_sessions(sessions),
        recent_tasks=recent_tasks,
        status_distribution=status_dist,
    )
