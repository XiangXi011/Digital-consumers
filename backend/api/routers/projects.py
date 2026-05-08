"""Project management API backed by TaskSessionManager."""

import json
import uuid

import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.domain.business_brief import BusinessBrief
from backend.paths import DEBUG_SESSIONS_DIR, DINGTALK_SESSIONS_DIR, OUTPUTS_DIR, PERSONA_COMPLETE_PATH
from backend.research.qualitative_research import ResearchPlannerBlockedError
from backend.workflow.dingtalk_bot import DingTalkBotWorkflow
from backend.workflow.task_session_manager import TaskSession, TaskSessionManager

logger = structlog.get_logger(__name__)

router = APIRouter()

SESSIONS_DIR = DINGTALK_SESSIONS_DIR
PERSONA_PATH = PERSONA_COMPLETE_PATH
_WEB_WORKFLOW = None


class CreateProjectRequest(BaseModel):
    name: str
    project_type: str = "concept"
    persona_ids: List[str] = Field(default_factory=list)
    business_brief: str = ""
    product_info: str = ""
    copy_material: str = ""
    user_question: str = ""
    mode: str = "multi"
    attachments: List[str] = Field(default_factory=list)
    enable_group_discussion: bool = False
    enable_deep_dive: bool = False


class ProjectSummary(BaseModel):
    session_id: str
    name: str = ""
    status: str = "collecting"
    project_type: str = ""
    created_at: str = ""
    has_report: bool = False
    html_report_path: Optional[str] = None
    json_report_path: Optional[str] = None


class ProjectDetail(ProjectSummary):
    fields: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    business_brief: Optional[Dict[str, Any]] = None
    readiness_decision: Optional[Dict[str, Any]] = None
    attachments: List[str] = Field(default_factory=list)
    attachment_urls: List[str] = Field(default_factory=list)
    research_plan: Optional[Dict[str, Any]] = None
    metrics_path: Optional[str] = None


class ProjectListResponse(BaseModel):
    projects: List[ProjectSummary]
    total: int


class ProjectRunStatus(BaseModel):
    session_id: str
    status: str
    current_stage: str
    progress: int
    last_error: Optional[str] = None
    updated_at: str = ""
    has_report: bool = False


PROJECT_TYPE_TO_QUESTION_TYPE = {
    "concept": "concept_test",
    "packaging": "packaging_review",
    "copywriting": "copy_feedback",
    "ab_test": "ab_test",
    "price": "price_test",
}


def _session_manager() -> TaskSessionManager:
    return TaskSessionManager(SESSIONS_DIR, persona_path=PERSONA_PATH)


def _project_type_label(question_type: str) -> str:
    return {
        "product_concept": "概念评审",
        "copy_feedback": "文案评审",
        "ab_test": "A/B测试",
        "price_test": "价格测试",
        "purchase_decision": "购买决策",
        "needs_pain_points": "需求痛点",
    }.get(question_type, question_type)


def _session_name(data: Dict[str, Any], fallback: str) -> str:
    fields = data.get("fields", {})
    user_q = fields.get("user_question", {})
    if isinstance(user_q, dict):
        value = str(user_q.get("value", "") or "").strip()
        if value:
            return value
    product = fields.get("product_info", {})
    if isinstance(product, dict):
        value = str(product.get("value", "") or "").strip()
        if value:
            return value[:50]
    return fallback[:30]


def _scan_sessions() -> List[Dict[str, Any]]:
    sessions: List[Dict[str, Any]] = []
    if not SESSIONS_DIR.exists():
        return sessions

    for path in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to parse session %s: %s", path.name, exc)
            continue
        fields = data.get("fields", {})
        question_field = fields.get("question_type", {})
        question_type = str(question_field.get("value", "") or "") if isinstance(question_field, dict) else ""
        sessions.append(
            {
                "session_id": data.get("session_id", path.stem),
                "name": _session_name(data, data.get("session_id", path.stem)),
                "status": data.get("status", "collecting"),
                "project_type": _project_type_label(question_type),
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "has_report": bool(data.get("html_report_path") or data.get("json_report_path")),
                "html_report_path": data.get("html_report_path"),
                "json_report_path": data.get("json_report_path"),
            }
        )
    return sessions


def _load_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    for scan_dir in [SESSIONS_DIR, DEBUG_SESSIONS_DIR]:
        if not scan_dir.exists():
            continue
        path = scan_dir / f"{session_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def _normalize_project_stage(status: str) -> str:
    stage_map = {
        "collecting": "collecting",
        "normalizing": "planning",
        "planning": "planning",
        "ready_to_dispatch": "planning",
        "running": "running",
        "dispatching": "running",
        "summarizing": "synthesizing",
        "awaiting_clarification": "awaiting_clarification",
        "awaiting_run_confirmation": "awaiting_run_confirmation",
        "awaiting_authorization": "awaiting_run_confirmation",
        "completed": "completed",
        "error": "error",
        "recovery": "error",
        "expired": "error",
    }
    return stage_map.get((status or "").strip(), "collecting")


def _status_progress(status: str, has_report: bool) -> int:
    if has_report or status == "completed":
        return 100
    progress_map = {
        "collecting": 10,
        "normalizing": 20,
        "planning": 35,
        "ready_to_dispatch": 50,
        "running": 70,
        "dispatching": 75,
        "summarizing": 90,
        "awaiting_clarification": 25,
        "awaiting_run_confirmation": 45,
        "awaiting_authorization": 45,
        "error": 0,
        "recovery": 0,
        "expired": 0,
    }
    return progress_map.get((status or "").strip(), 10)


def _extract_last_error(session_data: Dict[str, Any]) -> Optional[str]:
    readiness = session_data.get("readiness_decision") or {}
    if isinstance(readiness, dict):
        reasons = readiness.get("blocking_reasons")
        if isinstance(reasons, list) and reasons:
            return f"blocking_reasons: {', '.join(str(r) for r in reasons)}"

    if (session_data.get("status") or "").strip() == "error":
        return "任务执行失败，请查看服务日志定位具体异常"
    return None


def _get_web_workflow():
    global _WEB_WORKFLOW
    if _WEB_WORKFLOW is None:
        _WEB_WORKFLOW = DingTalkBotWorkflow(
            persona_path=PERSONA_PATH,
            session_dir=SESSIONS_DIR,
            output_dir=OUTPUTS_DIR,
        )
    return _WEB_WORKFLOW


def _build_business_brief(session: TaskSession):
    return BusinessBrief.from_session_fields(
        session.fields,
        source_links=list(getattr(session, "source_links", [])),
        custom_questions=list(getattr(session, "custom_questions", [])),
        product_context_notes=list(getattr(session, "product_context_notes", [])),
    )


def _build_readiness_decision(session: TaskSession, brief: Dict[str, Any]) -> Dict[str, Any]:
    parsed = BusinessBrief.model_validate(brief)
    blocking_reasons: List[str] = []
    product_context_lines = [line.strip() for line in parsed.product_context.splitlines() if line.strip()]
    has_substantive_product_context = any(
        not line.lower().startswith("source_links:") for line in product_context_lines
    )

    if not parsed.research_goal.strip():
        blocking_reasons.append("research_goal")
    if not has_substantive_product_context:
        blocking_reasons.append("product_context")
    if session.fields["mode"]["value"] == "single" and not session.fields["persona_id"]["value"]:
        blocking_reasons.append("persona_id")
    if parsed.task_type in {"copy_feedback", "ab_test"} and not (parsed.copy_candidates or parsed.key_claims):
        blocking_reasons.append("copy_candidates")
    if parsed.task_type == "price_test":
        if not parsed.price_test_mode:
            blocking_reasons.append("price_test_mode")
        if not parsed.price_range:
            blocking_reasons.append("price_range")
        if parsed.price_test_mode == "relative_price" and not parsed.benchmark_reference:
            blocking_reasons.append("benchmark_reference")

    recommended_state = "ready_to_dispatch" if not blocking_reasons else "awaiting_clarification"
    return {
        "recommended_state": recommended_state,
        "blocking_reasons": blocking_reasons,
        "authorization_needed": False,
    }


def _set_field(session: TaskSession, key: str, value: Any) -> None:
    text = "" if value is None else str(value).strip()
    state = session.fields[key]
    state["status"] = "provided" if text else "missing"
    state["value"] = text or None


def _normalize_attachment_ref(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    if text.startswith("web_uploads/"):
        return text
    marker = "/outputs/web_uploads/"
    if marker in text:
        return f"web_uploads/{text.split(marker, 1)[1]}"
    marker_windows = "\\outputs\\web_uploads\\"
    if marker_windows in str(value or ""):
        return f"web_uploads/{str(value).split(marker_windows, 1)[1].replace('\\', '/')}"
    return text


def _attachment_url(ref: str) -> str:
    text = str(ref or "").strip().replace("\\", "/")
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith("/outputs/"):
        return text
    if text.startswith("outputs/"):
        return f"/{text}"
    if text.startswith("web_uploads/"):
        return f"/outputs/{text}"
    return text


def _execute_project_run(session_id: str, workflow=None) -> None:
    workflow = workflow or _get_web_workflow()
    session = workflow.session_manager.load(session_id)
    brief = _build_business_brief(session)
    brief_payload = brief.model_dump()
    readiness_decision = _build_readiness_decision(session, brief_payload)
    session.business_brief = brief_payload
    session.readiness_decision = readiness_decision

    if readiness_decision["recommended_state"] != "ready_to_dispatch":
        session.status = "awaiting_clarification"
        workflow.session_manager.save(session)
        return

    try:
        research_input_payload = workflow.session_manager.build_research_input_payload(
            session,
            business_brief=brief_payload,
        )
        research_input = workflow.research_input_cls(**research_input_payload)
        session.status = "planning"
        workflow.session_manager.save(session)

        research_plan = workflow.runner.plan(research_input)
        session.research_plan = research_plan
        session.partial_run_authorized = True
        session.status = "running"
        session.last_task_id = f"{session.session_id}__run"
        workflow.session_manager.save_frozen_snapshot(
            session,
            "dispatch",
            {
                "business_brief": brief_payload,
                "research_input": research_input_payload,
                "research_plan": research_plan,
            },
        )
        workflow.session_manager.save(session)
        workflow.run_pending_task(session.last_task_id)
    except ResearchPlannerBlockedError as exc:
        session.status = "awaiting_clarification"
        session.research_plan = exc.research_plan
        session.last_task_id = None
        workflow.session_manager.save(session)
    except Exception:
        logger.exception("Web project execution failed for session_id=%s", session_id)
        session.status = "error"
        workflow.session_manager.save(session)


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(user=Depends(get_current_user)):
    projects = [ProjectSummary(**item) for item in _scan_sessions()]
    return ProjectListResponse(projects=projects, total=len(projects))


@router.get("/projects/{session_id}", response_model=ProjectDetail)
def get_project(session_id: str, user=Depends(get_current_user)):
    data = _load_session_data(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Project {session_id} not found")

    session_path = SESSIONS_DIR / f"{session_id}.json"
    question_field = (data.get("fields", {}).get("question_type", {}) or {})
    question_type = str(question_field.get("value", "") or "") if isinstance(question_field, dict) else ""
    attachments = [str(v) for v in data.get("attachments", []) if str(v).strip()]
    return ProjectDetail(
        session_id=data.get("session_id", session_id),
        name=_session_name(data, session_id),
        status=data.get("status", "collecting"),
        project_type=_project_type_label(question_type),
        created_at=datetime.fromtimestamp(session_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        if session_path.exists()
        else "",
        has_report=bool(data.get("html_report_path") or data.get("json_report_path")),
        html_report_path=data.get("html_report_path"),
        json_report_path=data.get("json_report_path"),
        fields=data.get("fields", {}),
        missing_fields=data.get("missing_fields", []),
        business_brief=data.get("business_brief"),
        readiness_decision=data.get("readiness_decision"),
        attachments=attachments,
        attachment_urls=[u for u in (_attachment_url(v) for v in attachments) if u],
        research_plan=data.get("research_plan"),
        metrics_path=data.get("metrics_path"),
    )


@router.post("/projects", response_model=ProjectSummary)
def create_project(request: CreateProjectRequest, user=Depends(get_current_user)):
    manager = _session_manager()
    session_id = uuid.uuid4().hex
    mode = request.mode or ("single" if len(request.persona_ids) == 1 else "multi")
    session = TaskSession(
        session_id=session_id,
        group_id=f"web::{session_id}",
        conversation_id=f"web::{session_id}",
        user_id="web-ui",
        status="collecting",
    )

    _set_field(session, "mode", mode)
    _set_field(session, "question_type", PROJECT_TYPE_TO_QUESTION_TYPE.get(request.project_type, "product_concept"))
    _set_field(session, "user_question", request.user_question or request.name)
    _set_field(session, "background_material", request.business_brief)
    _set_field(session, "product_info", request.product_info)
    _set_field(session, "copy_material", request.copy_material)
    if request.persona_ids:
        _set_field(session, "persona_id", ",".join(request.persona_ids))
    session.attachments = [
        item for item in (_normalize_attachment_ref(v) for v in request.attachments) if item
    ]
    # Phase 3: persist research methodology flags
    _set_field(session, "enable_group_discussion", str(request.enable_group_discussion))
    _set_field(session, "enable_deep_dive", str(request.enable_deep_dive))
    session.missing_fields = manager.get_missing_fields(session)
    manager.save(session)

    return ProjectSummary(
        session_id=session.session_id,
        name=request.name,
        status=session.status,
        project_type=request.project_type,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@router.get("/projects/{session_id}/status", response_model=ProjectRunStatus)
def get_project_status(session_id: str, user=Depends(get_current_user)):
    data = _load_session_data(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Project {session_id} not found")

    status = str(data.get("status", "collecting") or "collecting")
    has_report = bool(data.get("html_report_path") or data.get("json_report_path"))
    stage = _normalize_project_stage(status)

    session_path = SESSIONS_DIR / f"{session_id}.json"
    updated_at = ""
    if session_path.exists():
        updated_at = datetime.fromtimestamp(session_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    return ProjectRunStatus(
        session_id=session_id,
        status=status,
        current_stage=stage,
        progress=_status_progress(status, has_report),
        last_error=_extract_last_error(data),
        updated_at=updated_at,
        has_report=has_report,
    )


@router.post("/projects/{session_id}/run")
def run_project(
    session_id: str,
    background_tasks: BackgroundTasks,
    use_celery: bool = Query(default=True, description="Use Celery for durable task execution"),
    user=Depends(get_current_user),
):
    data = _load_session_data(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Project {session_id} not found")

    workflow = _get_web_workflow()
    session = workflow.session_manager.load(session_id)

    task_id = None
    if use_celery:
        try:
            from backend.tasks.project_tasks import execute_project_run

            result = execute_project_run.delay(session_id)
            task_id = result.id
            logger.info("Celery task dispatched: task_id=%s session_id=%s", task_id, session_id)
        except Exception:
            logger.warning("Celery broker unavailable, falling back to BackgroundTasks")
            background_tasks.add_task(_execute_project_run, session_id)
    else:
        background_tasks.add_task(_execute_project_run, session_id)

    return {
        "session_id": session_id,
        "status": "running",
        "current_stage": _normalize_project_stage("running"),
        "progress": _status_progress("running", False),
        "task_id": task_id,
    }


@router.get("/projects/{session_id}/task-status")
def get_task_status(session_id: str, user=Depends(get_current_user)):
    """Get Celery task status for a project run."""
    try:
        from backend.tasks.celery_app import celery_app

        # Find task result by session_id from the project's last_task_id
        data = _load_session_data(session_id)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Project {session_id} not found")

        task_id = data.get("celery_task_id")
        if not task_id:
            # Fallback: return project status from session data
            status = str(data.get("status", "collecting") or "collecting")
            return {
                "session_id": session_id,
                "task_id": None,
                "task_state": "UNKNOWN",
                "project_status": status,
            }

        result = celery_app.AsyncResult(task_id)
        return {
            "session_id": session_id,
            "task_id": task_id,
            "task_state": result.state,
            "task_result": result.result if result.ready() else None,
            "project_status": str(data.get("status", "collecting") or "collecting"),
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="Celery is not available")
