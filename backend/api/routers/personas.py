"""Persona library API backed by personas/*.yaml and persona_samples.json."""

import json
import random

import structlog
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Annotated

from backend.auth.dependencies import get_current_user, require_role
from backend.paths import PERSONAS_DIR, PERSONA_SAMPLES_PATH

logger = structlog.get_logger(__name__)

router = APIRouter()


class PersonaSummary(BaseModel):
    id: str
    name: str
    budget_band: str = ""
    tags: List[str] = Field(default_factory=list)
    decision_weights: Dict[str, float] = Field(default_factory=dict)


class VetoRule(BaseModel):
    code: str
    description: str


class PersonaDetail(PersonaSummary):
    veto_trigger: str = ""
    veto_rules: List[VetoRule] = Field(default_factory=list)
    feature_scoring_rubric: Dict[str, Any] = Field(default_factory=dict)
    representative_samples: List[Dict[str, Any]] = Field(default_factory=list)


class PersonaListResponse(BaseModel):
    personas: List[PersonaSummary]
    total: int


def _load_persona_yaml(yaml_path: Path) -> Dict[str, Any]:
    import yaml

    return yaml.safe_load(yaml_path.read_text(encoding="utf-8"))


def _load_all_personas() -> Dict[str, Dict[str, Any]]:
    personas: Dict[str, Dict[str, Any]] = {}
    for path in sorted(PERSONAS_DIR.glob("M*.yaml")):
        try:
            data = _load_persona_yaml(path)
            personas[data["id"]] = data
        except Exception as exc:
            logger.warning("Failed to load persona %s: %s", path.name, exc)
    return personas


def _extract_tags(persona: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    budget = persona.get("budget_band", "")
    if budget:
        budget_labels = {"high": "高预算", "mid": "中预算", "low": "低预算"}
        tags.append(budget_labels.get(budget, budget))
    trigger = persona.get("veto_trigger", "")
    if trigger:
        tags.extend([part.strip() for part in str(trigger).split("/") if part.strip()][:3])
    return tags


def _get_representative_samples(persona_id: str) -> List[Dict[str, Any]]:
    if not PERSONA_SAMPLES_PATH.exists():
        return []
    try:
        data = json.loads(PERSONA_SAMPLES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [sample for sample in data.get("samples", []) if sample.get("segment_id") == persona_id]


def _persona_to_summary(data: Dict[str, Any]) -> PersonaSummary:
    return PersonaSummary(
        id=data.get("id", ""),
        name=data.get("name", ""),
        budget_band=data.get("budget_band", ""),
        tags=_extract_tags(data),
        decision_weights=data.get("decision_weights", {}),
    )


def _persona_to_detail(data: Dict[str, Any]) -> PersonaDetail:
    veto_rules: List[VetoRule] = []
    if isinstance(data.get("veto_rules"), list):
        for rule in data["veto_rules"]:
            if isinstance(rule, dict):
                veto_rules.append(
                    VetoRule(
                        code=str(rule.get("code", "")),
                        description=str(rule.get("description", "")),
                    )
                )

    return PersonaDetail(
        id=data.get("id", ""),
        name=data.get("name", ""),
        budget_band=data.get("budget_band", ""),
        tags=_extract_tags(data),
        decision_weights=data.get("decision_weights", {}),
        veto_trigger=data.get("veto_trigger", ""),
        veto_rules=veto_rules,
        feature_scoring_rubric=data.get("feature_scoring_rubric", {}),
        representative_samples=_get_representative_samples(data.get("id", "")),
    )


@router.get("/personas", response_model=PersonaListResponse)
def list_personas(user=Depends(get_current_user)):
    all_personas = _load_all_personas()
    summaries = [_persona_to_summary(persona) for persona in all_personas.values()]
    return PersonaListResponse(personas=summaries, total=len(summaries))


@router.get("/personas/{persona_id}", response_model=PersonaDetail)
def get_persona(persona_id: str, user=Depends(get_current_user)):
    yaml_path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
    try:
        return _persona_to_detail(_load_persona_yaml(yaml_path))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------- #
#  Persona CRUD (Editor+)                                                 #
# ---------------------------------------------------------------------- #

class CreatePersonaRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    budget_band: str = ""
    veto_trigger: str = ""
    decision_weights: Dict[str, float] = Field(default_factory=dict)
    veto_rules: List[VetoRule] = Field(default_factory=list)
    feature_scoring_rubric: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class UpdatePersonaRequest(BaseModel):
    name: Optional[str] = None
    budget_band: Optional[str] = None
    veto_trigger: Optional[str] = None
    decision_weights: Optional[Dict[str, float]] = None
    veto_rules: Optional[List[VetoRule]] = None
    feature_scoring_rubric: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


@router.post("/personas", response_model=PersonaDetail)
def create_persona(
    request: CreatePersonaRequest,
    user=Depends(require_role("editor")),
):
    """Create a custom persona (Editor+ only)."""
    import yaml as _yaml

    yaml_path = PERSONAS_DIR / f"{request.id}.yaml"
    if yaml_path.exists():
        raise HTTPException(status_code=409, detail=f"Persona {request.id} already exists")

    persona_data = {
        "id": request.id,
        "name": request.name,
        "budget_band": request.budget_band,
        "veto_trigger": request.veto_trigger,
        "decision_weights": request.decision_weights,
        "veto_rules": [r.model_dump() for r in request.veto_rules],
        "feature_scoring_rubric": request.feature_scoring_rubric,
        "tags": request.tags,
    }
    yaml_path.write_text(
        _yaml.dump(persona_data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    logger.info("Created custom persona %s by user %s", request.id, user.email)
    return _persona_to_detail(persona_data)


@router.put("/personas/{persona_id}", response_model=PersonaDetail)
def update_persona(
    persona_id: str,
    request: UpdatePersonaRequest,
    user=Depends(require_role("editor")),
):
    """Update an existing persona (Editor+ only)."""
    import yaml as _yaml

    yaml_path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    persona_data = _load_persona_yaml(yaml_path)

    # Apply partial updates
    update_fields = request.model_dump(exclude_unset=True)
    if "veto_rules" in update_fields:
        update_fields["veto_rules"] = [
            r if isinstance(r, dict) else r for r in update_fields["veto_rules"]
        ]
    persona_data.update(update_fields)

    yaml_path.write_text(
        _yaml.dump(persona_data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    logger.info("Updated persona %s by user %s", persona_id, user.email)
    return _persona_to_detail(persona_data)


@router.delete("/personas/{persona_id}")
def delete_persona(
    persona_id: str,
    user=Depends(require_role("admin")),
):
    """Delete a custom persona (Admin only). Built-in M01-M08 cannot be deleted."""
    if persona_id.startswith("M0") and persona_id[2:].isdigit() and 1 <= int(persona_id[2:]) <= 8:
        raise HTTPException(status_code=403, detail="Cannot delete built-in persona")

    yaml_path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    yaml_path.unlink()
    logger.info("Deleted persona %s by user %s", persona_id, user.email)
    return {"deleted": persona_id}


# ---------------------------------------------------------------------- #
#  Sample randomization                                                   #
# ---------------------------------------------------------------------- #

@router.get("/personas/{persona_id}/samples")
def get_persona_samples(
    persona_id: str,
    count: int = Query(default=3, ge=1, le=25, description="Number of samples to return"),
    seed: Optional[int] = Query(default=None, description="Random seed for reproducibility"),
    user=Depends(get_current_user),
):
    """Get representative samples for a persona with optional randomization.

    If `count` < total available samples, randomly selects `count` samples.
    Use `seed` for reproducible results across runs.
    """
    if not PERSONA_SAMPLES_PATH.exists():
        raise HTTPException(status_code=404, detail="Samples data not found")

    try:
        data = json.loads(PERSONA_SAMPLES_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load samples: {exc}")

    all_samples = [
        sample for sample in data.get("samples", [])
        if sample.get("segment_id") == persona_id
    ]

    if not all_samples:
        raise HTTPException(status_code=404, detail=f"No samples found for persona {persona_id}")

    if count >= len(all_samples):
        selected = all_samples
    else:
        rng = random.Random(seed)
        selected = rng.sample(all_samples, count)

    return {
        "persona_id": persona_id,
        "total_available": len(all_samples),
        "returned": len(selected),
        "seed": seed,
        "samples": selected,
    }
