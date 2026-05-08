"""Report center API for JSON/HTML reports under outputs/."""

import json
import structlog
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.paths import DINGTALK_REPORTS_DIR, OUTPUTS_DIR, REPORT_SHARES_PATH

logger = structlog.get_logger(__name__)

router = APIRouter()


class ReportSummary(BaseModel):
    id: str
    name: str
    report_type: str = ""
    date: str = ""
    status: str = "completed"
    has_html: bool = False
    json_path: str = ""
    html_path: str = ""


class ReportListResponse(BaseModel):
    reports: List[ReportSummary]
    total: int
    page: int
    page_size: int


class ShareReportResponse(BaseModel):
    success: bool = True
    report_id: str
    share_token: str
    share_url: str
    expires_at: str
    revoked: bool = False
    message: str = "分享链接已生成"


def _normalized_report_payload(report_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    brief = payload.get("research_brief") if isinstance(payload.get("research_brief"), dict) else {}
    voices_raw = payload.get("consumer_voice") if isinstance(payload.get("consumer_voice"), list) else []
    synthesis = payload.get("synthesis") if isinstance(payload.get("synthesis"), dict) else {}
    metrics = payload.get("evaluation_metrics") if isinstance(payload.get("evaluation_metrics"), dict) else {}

    if not isinstance(synthesis.get("research_summary"), dict):
        synthesis["research_summary"] = payload.get("research_summary", {}) if isinstance(payload.get("research_summary"), dict) else {}
    if not isinstance(synthesis.get("structured_recommendation"), dict):
        synthesis["structured_recommendation"] = payload.get("structured_recommendation", {}) if isinstance(payload.get("structured_recommendation"), dict) else {}

    normalized_voices: List[Dict[str, Any]] = []
    for voice in voices_raw:
        if not isinstance(voice, dict):
            continue
        be = voice.get("backend_evaluation") if isinstance(voice.get("backend_evaluation"), dict) else {}
        intent = be.get("purchase_intent") or voice.get("purchase_intent") or "unknown"
        score = be.get("purchase_score")
        if score is None:
            score = voice.get("purchase_score", 0)

        normalized_voices.append(
            {
                "persona_id": voice.get("persona_id", ""),
                "persona_name": voice.get("persona_name") or voice.get("persona_id", ""),
                "stance": voice.get("stance", ""),
                "voice_line": voice.get("voice_line") or voice.get("verbatim_answer", ""),
                "purchase_intent": intent,
                "purchase_score": score,
                "rubric_scores": voice.get("rubric_scores", {}) if isinstance(voice.get("rubric_scores"), dict) else {},
                "backend_evaluation": be,
            }
        )

    return {
        "id": report_id,
        "meta": {
            "report_title": meta.get("report_title") or brief.get("research_goal") or report_id,
            "created_at": meta.get("created_at", ""),
            "question_type": meta.get("question_type") or brief.get("task_type", "unknown"),
        },
        "research_brief": {
            "research_goal": brief.get("research_goal", ""),
            "task_type": brief.get("task_type", ""),
            "product_context": brief.get("product_context", ""),
        },
        "consumer_voice": normalized_voices,
        "synthesis": {
            "research_summary": synthesis.get("research_summary", {}),
            "structured_recommendation": synthesis.get("structured_recommendation", {}),
        },
        "evaluation_metrics": {
            "pipeline_total_latency_ms": metrics.get("pipeline_total_latency_ms", 0),
            "inter_persona_divergence_score": metrics.get("inter_persona_divergence_score", 0),
            "minority_survival_rate": metrics.get("minority_survival_rate", 0),
            "repeated_phrase_rate": metrics.get("repeated_phrase_rate", 0),
        },
    }


def _scan_reports() -> List[Dict[str, Any]]:
    reports: List[Dict[str, Any]] = []
    for scan_dir in [OUTPUTS_DIR, DINGTALK_REPORTS_DIR]:
        if not scan_dir.exists():
            continue
        for json_path in sorted(scan_dir.glob("*.json"), reverse=True):
            name = json_path.stem
            if name.startswith(".") or "debug" in name or "samples" in name:
                continue
            if "consistency_check" in name or "diversity_check" in name:
                continue
            if "persona_constraint" in name or "persona_report" in name or "simulation_report" in name:
                continue
            if "report_shares" in name:
                continue

            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                meta = data.get("meta", {})
                report_type = meta.get("question_type") or data.get("research_brief", {}).get("task_type", "unknown")
                created = meta.get("created_at", "")
                date_str = str(created)[:19] if created else datetime.fromtimestamp(json_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                html_path = json_path.with_suffix(".html")
                type_labels = {
                    "concept_test": "概念评审",
                    "product_concept": "概念评审",
                    "copy_feedback": "文案评审",
                    "ab_test": "A/B测试",
                    "price_test": "价格测试",
                    "purchase_decision": "购买决策",
                    "needs_pain_points": "需求痛点",
                }
                reports.append(
                    {
                        "id": name,
                        "name": meta.get("report_title", "") or name.replace("_report", "").replace("_", " "),
                        "report_type": type_labels.get(report_type, report_type),
                        "date": date_str,
                        "status": "completed",
                        "has_html": html_path.exists(),
                        "json_path": str(json_path),
                        "html_path": str(html_path) if html_path.exists() else "",
                        "_sort_key": json_path.stat().st_mtime,
                    }
                )
            except Exception as exc:
                logger.warning("Failed to parse report %s: %s", json_path.name, exc)
    # Sort by file mtime descending (newest first), then strip internal key
    reports.sort(key=lambda r: r.get("_sort_key", 0), reverse=True)
    for r in reports:
        r.pop("_sort_key", None)
    return reports


def _find_report_json_path(report_id: str):
    for scan_dir in [OUTPUTS_DIR, DINGTALK_REPORTS_DIR]:
        json_path = scan_dir / f"{report_id}.json"
        if json_path.exists():
            return json_path
    return None


def _load_share_store() -> Dict[str, Any]:
    if not REPORT_SHARES_PATH.exists():
        return {"shares": {}}
    try:
        data = json.loads(REPORT_SHARES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"shares": {}}
    shares = data.get("shares")
    if not isinstance(shares, dict):
        return {"shares": {}}
    return {"shares": shares}


def _save_share_store(store: Dict[str, Any]) -> None:
    REPORT_SHARES_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_SHARES_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@router.get("/reports", response_model=ReportListResponse)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query(""),
    report_type: str = Query(""),
    user=Depends(get_current_user),
):
    reports = _scan_reports()
    if search:
        lowered = search.lower()
        reports = [report for report in reports if lowered in report["name"].lower() or lowered in report["id"].lower()]
    if report_type:
        reports = [report for report in reports if report["report_type"] == report_type]

    total = len(reports)
    start = (page - 1) * page_size
    end = start + page_size
    return ReportListResponse(
        reports=[ReportSummary(**report) for report in reports[start:end]],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/{report_id}")
def get_report(report_id: str, user=Depends(get_current_user)):
    json_path = _find_report_json_path(report_id)
    if json_path is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        return _normalized_report_payload(report_id, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reports/{report_id}/html", response_class=HTMLResponse)
def get_report_html(report_id: str, user=Depends(get_current_user)):
    for scan_dir in [OUTPUTS_DIR, DINGTALK_REPORTS_DIR]:
        html_path = scan_dir / f"{report_id}.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail=f"HTML report {report_id} not found")


@router.get("/reports/{report_id}/download")
def download_report_json(report_id: str, user=Depends(get_current_user)):
    for scan_dir in [OUTPUTS_DIR, DINGTALK_REPORTS_DIR]:
        json_path = scan_dir / f"{report_id}.json"
        if json_path.exists():
            return FileResponse(
                path=str(json_path),
                media_type="application/json",
                filename=f"{report_id}.json",
            )
    raise HTTPException(status_code=404, detail=f"Report {report_id} not found")


@router.post("/reports/{report_id}/share", response_model=ShareReportResponse)
def share_report(report_id: str, user=Depends(get_current_user)):
    json_path = _find_report_json_path(report_id)
    if json_path is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    store = _load_share_store()
    store["shares"][token] = {
        "token": token,
        "report_id": report_id,
        "created_at": _now_iso(),
        "expires_at": expires_at,
        "revoked": False,
    }
    _save_share_store(store)

    return ShareReportResponse(
        report_id=report_id,
        share_token=token,
        share_url=f"/api/shared/reports/{token}",
        expires_at=expires_at,
    )


@router.get("/shared/reports/{token}")
def get_shared_report(token: str):
    store = _load_share_store()
    item = store.get("shares", {}).get(token)
    if not item:
        raise HTTPException(status_code=404, detail="Share token not found")
    if item.get("revoked"):
        raise HTTPException(status_code=410, detail="Share token has been revoked")

    expires_at = item.get("expires_at")
    if isinstance(expires_at, str) and expires_at:
        try:
            if datetime.now() > datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S"):
                raise HTTPException(status_code=410, detail="Share token has expired")
        except ValueError:
            logger.warning("Invalid expires_at format for token=%s", token)

    report_id = str(item.get("report_id", "") or "")
    if not report_id:
        raise HTTPException(status_code=500, detail="Invalid share record")

    json_path = _find_report_json_path(report_id)
    if json_path is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "share": {
            "token": token,
            "report_id": report_id,
            "expires_at": expires_at,
            "revoked": False,
        },
        "report": _normalized_report_payload(report_id, payload),
    }


@router.delete("/reports/{report_id}/share/{token}")
def revoke_share_token(report_id: str, token: str, user=Depends(get_current_user)):
    store = _load_share_store()
    item = store.get("shares", {}).get(token)
    if not item:
        raise HTTPException(status_code=404, detail="Share token not found")
    if str(item.get("report_id", "")) != report_id:
        raise HTTPException(status_code=400, detail="Share token does not belong to this report")

    item["revoked"] = True
    item["revoked_at"] = _now_iso()
    store["shares"][token] = item
    _save_share_store(store)

    return {
        "success": True,
        "report_id": report_id,
        "share_token": token,
        "revoked": True,
        "message": "分享链接已撤销",
    }
