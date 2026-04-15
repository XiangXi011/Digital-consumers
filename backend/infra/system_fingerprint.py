import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


PROMPT_VERSION = "qualitative-prompt-v1"
PROMPT_BUNDLE_VERSION = "prompt-bundle-v2"
SCHEMA_VERSION = "qualitative-report-v2"
PERSONA_PACK_VERSION = "persona-pack-v1"
ROUTER_VERSION = "routing-rule-engine-v1"
SYNTHESIS_VERSION = "evidence-first-ra-v1"
SCORING_ENGINE_VERSION = "persona-backend-scoring-v1"


def _safe_git_sha(base_dir: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=base_dir,
                text=True,
            )
            .strip()
        )
    except Exception:
        return "unknown"


def _detect_model_id(ai_client: Any | None) -> str:
    if ai_client is None:
        return "unknown"

    config = getattr(ai_client, "config", None)
    if config is not None:
        model = getattr(config, "model", "")
        if isinstance(model, str) and model.strip():
            return model.strip()

    model = getattr(ai_client, "model", "")
    if isinstance(model, str) and model.strip():
        return model.strip()

    return ai_client.__class__.__name__


def _detect_router_model(ai_client: Any | None) -> str:
    """Detect the routing / fast model id."""
    if ai_client is None:
        return "unknown"
    config = getattr(ai_client, "config", None)
    if config is not None:
        router = getattr(config, "router_model", "")
        if isinstance(router, str) and router.strip():
            return router.strip()
    return _detect_model_id(ai_client)


def _hash_persona_pack(base_dir: Path) -> str:
    """Compute a short hash of the persona YAML directory for traceability."""
    persona_dir = base_dir / "personas"
    if not persona_dir.is_dir():
        return PERSONA_PACK_VERSION
    hasher = hashlib.sha256()
    for yaml_file in sorted(persona_dir.glob("*.yaml")):
        hasher.update(yaml_file.read_bytes())
    return f"{PERSONA_PACK_VERSION}-{hasher.hexdigest()[:8]}"


def collect_version_bundle(base_dir: Path, ai_client: Any | None = None) -> Dict[str, str]:
    return {
        "prompt_bundle_version": PROMPT_BUNDLE_VERSION,
        "persona_pack_version": _hash_persona_pack(base_dir),
        "schema_version": SCHEMA_VERSION,
        "router_version": ROUTER_VERSION,
        "synthesis_version": SYNTHESIS_VERSION,
        "scoring_engine_version": SCORING_ENGINE_VERSION,
        "router_model_version": _detect_router_model(ai_client),
    }


def collect_system_fingerprint(base_dir: Path, ai_client: Any | None = None) -> Dict[str, str]:
    return {
        "git_sha": _safe_git_sha(base_dir),
        "env": os.environ.get("APP_ENV") or os.environ.get("ENV") or "dev",
        "model_id": _detect_model_id(ai_client),
        "prompt_version": PROMPT_VERSION,
        **collect_version_bundle(base_dir, ai_client=ai_client),
    }
