"""System settings API backed by the workspace .env file."""

import structlog
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth.dependencies import require_role
from backend.paths import DOTENV_PATH

logger = structlog.get_logger(__name__)

router = APIRouter()


class SystemSettings(BaseModel):
    llm_model: str = ""
    llm_api_base: str = ""
    llm_api_key_masked: str = ""
    dingtalk_app_key: str = ""
    dingtalk_app_secret_masked: str = ""
    dingtalk_enabled: bool = True
    prompt_shield_enabled: bool = True
    pii_sanitization_enabled: bool = True
    langsmith_tracing: bool = True
    langsmith_project: str = ""


class UpdateSettingsRequest(BaseModel):
    llm_model: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_api_key: Optional[str] = None
    dingtalk_app_key: Optional[str] = None
    dingtalk_app_secret: Optional[str] = None
    prompt_shield_enabled: Optional[bool] = None
    pii_sanitization_enabled: Optional[bool] = None
    langsmith_tracing: Optional[bool] = None
    langsmith_project: Optional[str] = None


class ConnectionTestResult(BaseModel):
    success: bool
    latency_ms: float = 0.0
    model: str = ""
    error: str = ""


def _load_env() -> dict[str, str]:
    if not DOTENV_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _mask_key(value: str) -> str:
    if not value or len(value) < 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def _save_env(updates: dict[str, str]):
    lines = DOTENV_PATH.read_text(encoding="utf-8").splitlines() if DOTENV_PATH.exists() else []
    updated_keys = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")
    DOTENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.get("/settings", response_model=SystemSettings)
def get_settings(user=Depends(require_role("admin", "editor", "viewer"))):
    env = _load_env()
    prompt_shield_raw = env.get("PROMPT_SHIELD_ENABLED", "true").strip().lower()
    pii_raw = env.get("PII_SANITIZATION_ENABLED", "true").strip().lower()
    langsmith_raw = env.get("LANGSMITH_TRACING", "false").strip().lower()

    return SystemSettings(
        llm_model=env.get("OPENAI_MODEL", ""),
        llm_api_base=env.get("OPENAI_BASE_URL", ""),
        llm_api_key_masked=_mask_key(env.get("OPENAI_API_KEY", "")),
        dingtalk_app_key=env.get("DINGTALK_APP_KEY", ""),
        dingtalk_app_secret_masked=_mask_key(env.get("DINGTALK_APP_SECRET", "")),
        dingtalk_enabled=bool(env.get("DINGTALK_APP_KEY")),
        prompt_shield_enabled=prompt_shield_raw in {"1", "true", "yes", "on"},
        pii_sanitization_enabled=pii_raw in {"1", "true", "yes", "on"},
        langsmith_tracing=langsmith_raw in {"1", "true", "yes", "on"},
        langsmith_project=env.get("LANGSMITH_PROJECT", ""),
    )


@router.put("/settings", response_model=SystemSettings)
def update_settings(request: UpdateSettingsRequest, user=Depends(require_role("admin"))):
    updates: dict[str, str] = {}
    if request.llm_model is not None:
        updates["OPENAI_MODEL"] = request.llm_model
    if request.llm_api_base is not None:
        updates["OPENAI_BASE_URL"] = request.llm_api_base
    if request.llm_api_key is not None:
        updates["OPENAI_API_KEY"] = request.llm_api_key
    if request.dingtalk_app_key is not None:
        updates["DINGTALK_APP_KEY"] = request.dingtalk_app_key
    if request.dingtalk_app_secret is not None:
        updates["DINGTALK_APP_SECRET"] = request.dingtalk_app_secret
    if request.prompt_shield_enabled is not None:
        updates["PROMPT_SHIELD_ENABLED"] = "true" if request.prompt_shield_enabled else "false"
    if request.pii_sanitization_enabled is not None:
        updates["PII_SANITIZATION_ENABLED"] = "true" if request.pii_sanitization_enabled else "false"
    if request.langsmith_tracing is not None:
        updates["LANGSMITH_TRACING"] = "true" if request.langsmith_tracing else "false"
    if request.langsmith_project is not None:
        updates["LANGSMITH_PROJECT"] = request.langsmith_project

    if updates:
        _save_env(updates)
        logger.info("Settings updated: %s", list(updates.keys()))
    return get_settings()


@router.post("/settings/test-connection", response_model=ConnectionTestResult)
def test_llm_connection(user=Depends(require_role("admin"))):
    import time

    env = _load_env()
    api_key = env.get("OPENAI_API_KEY", "")
    base_url = env.get("OPENAI_BASE_URL", "")
    model = env.get("OPENAI_MODEL", "")
    if not api_key or not base_url:
        return ConnectionTestResult(success=False, error="API Key 或 Base URL 未配置", model=model)

    try:
        from openai import OpenAI

        start = time.time()
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15)
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        return ConnectionTestResult(
            success=True,
            latency_ms=round((time.time() - start) * 1000, 1),
            model=model,
        )
    except Exception as exc:
        return ConnectionTestResult(success=False, error=str(exc)[:200], model=model)
