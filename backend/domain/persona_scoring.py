"""
Backend math-decoupled persona scoring.

Loads decision_weights and veto_trigger from persona YAML files.
Computes purchase_score and purchase_intent in backend code — 
never inside the LLM.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from backend.domain.evidence_models import DEFAULT_WEIGHTS, PersonaEvaluation
from backend.domain.scoring_registry import get_scoring_config


# ---------------------------------------------------------------------- #
#  YAML loader                                                            #
# ---------------------------------------------------------------------- #

def load_persona_yaml(yaml_path: Path) -> Dict[str, Any]:
    """Load a single persona YAML file."""
    return yaml.safe_load(yaml_path.read_text(encoding="utf-8"))


def load_all_persona_yamls(personas_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all persona YAML files from a directory, keyed by persona id."""
    personas: Dict[str, Dict[str, Any]] = {}
    for path in sorted(personas_dir.glob("M*.yaml")):
        data = load_persona_yaml(path)
        personas[data["id"]] = data
    return personas


def get_decision_weights(persona_yaml: Dict[str, Any]) -> Dict[str, float]:
    """Extract decision_weights from a persona YAML, falling back to defaults."""
    return persona_yaml.get("decision_weights", dict(DEFAULT_WEIGHTS))


def get_veto_trigger(persona_yaml: Dict[str, Any]) -> str:
    """Extract veto_trigger text from a persona YAML."""
    return persona_yaml.get("veto_trigger", "")


def get_rubric(persona_yaml: Dict[str, Any]) -> Dict[str, Dict[int, str]]:
    """Extract the feature_scoring_rubric from a persona YAML."""
    return persona_yaml.get("feature_scoring_rubric", {})


def _get_veto_rules(persona_yaml: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules = persona_yaml.get("veto_rules")
    if isinstance(rules, list) and rules:
        normalized = []
        for index, rule in enumerate(rules, start=1):
            if not isinstance(rule, dict):
                continue
            code = str(rule.get("code") or f"legacy_veto_{index}").strip()
            if not code:
                continue
            normalized.append(
                {
                    "code": code,
                    "description": str(rule.get("description", "")).strip(),
                }
            )
        if normalized:
            return normalized

    trigger_text = get_veto_trigger(persona_yaml)
    conditions = [c.strip() for c in trigger_text.split("/") if c.strip()]
    return [
        {"code": f"legacy_veto_{index}", "description": condition}
        for index, condition in enumerate(conditions, start=1)
    ]


# ---------------------------------------------------------------------- #
#  Veto detection                                                         #
# ---------------------------------------------------------------------- #

def check_veto(
    persona_yaml: Dict[str, Any],
    product_context: str,
    persona_output: Dict[str, Any],
) -> bool:
    """Check whether the veto trigger fires for a given persona output.

    Examines the persona's veto_trigger text against the product context
    and low scores from the persona output.
    """
    triggered_codes = persona_output.get("triggered_veto_codes", [])
    if isinstance(triggered_codes, list):
        normalized_codes = {str(code).strip() for code in triggered_codes if str(code).strip()}
        if normalized_codes:
            allowed_codes = {
                str(rule.get("code", "")).strip()
                for rule in _get_veto_rules(persona_yaml)
                if str(rule.get("code", "")).strip()
            }
            if not allowed_codes or normalized_codes & allowed_codes:
                return True

    trigger_text = get_veto_trigger(persona_yaml)
    conditions = [c.strip() for c in trigger_text.split("/") if c.strip()]
    if not conditions:
        scores = persona_output.get("rubric_scores", {})
        return any(v == 1 for v in scores.values() if isinstance(v, int))

    combined_text = f"{product_context} {persona_output.get('verbatim_answer', '')}"
    combined_text_lower = combined_text.lower()

    for condition in conditions:
        # Simple keyword match in the combined context
        keywords = [kw.strip() for kw in re.split(r"[，、,]", condition) if kw.strip()]
        if any(kw in combined_text_lower for kw in keywords):
            return True

    # Also trigger veto if any dimension score is 1 (minimum)
    scores = persona_output.get("rubric_scores", {})
    if any(v == 1 for v in scores.values() if isinstance(v, int)):
        return True

    return False


# ---------------------------------------------------------------------- #
#  Main scoring function                                                  #
# ---------------------------------------------------------------------- #

def compute_purchase_intent(
    rubric_scores: Dict[str, int],
    persona_yaml: Dict[str, Any],
    product_context: str = "",
    persona_output: Optional[Dict[str, Any]] = None,
    task_type: str = "",
) -> PersonaEvaluation:
    """Compute purchase intent from discrete 1-5 rubric scores.

    This is the ONLY place that produces purchase_score and purchase_intent.
    Persona LLM nodes must never compute these values.

    Supports both legacy fixed dimensions and dynamic per-task-type dimensions
    via scoring_registry.

    Args:
        rubric_scores: dict with dimension keys (dynamic per task_type or legacy).
                      Each value is an int 1-5.
        persona_yaml: loaded persona YAML dict (for weights and veto).
        product_context: product description text for veto checking.
        persona_output: full persona LLM output dict for veto checking.
        task_type: review type (e.g. "concept_test", "packaging_review").
                  If provided, uses scoring_registry for weights/thresholds.

    Returns:
        PersonaEvaluation with computed purchase_score and purchase_intent.
    """
    # Use task_type-specific weights if available, else persona YAML weights
    if task_type:
        config = get_scoring_config(task_type)
        weights = config["weights"]
        buy_threshold = config["buy_threshold"]
        reject_threshold = config["reject_threshold"]
    else:
        weights = get_decision_weights(persona_yaml)
        buy_threshold = 4.0
        reject_threshold = 2.8

    veto = check_veto(persona_yaml, product_context, persona_output or {})

    # Build legacy fields from rubric_scores for backward compat
    legacy_fields = {
        "efficacy_clarity": rubric_scores.get("efficacy_clarity", 3),
        "trust_signal": rubric_scores.get("trust_signal", 3),
        "convenience": rubric_scores.get("convenience", 3),
        "price_fit": rubric_scores.get("price_fit", 3),
    }

    return PersonaEvaluation(
        persona_id=persona_yaml.get("id", ""),
        persona_name=persona_yaml.get("name", ""),
        rubric_scores=rubric_scores,
        **legacy_fields,
        veto_triggered=veto,
        decision_weights=weights,
        buy_threshold=buy_threshold,
        reject_threshold=reject_threshold,
    )


def compute_batch_intent(
    all_rubric_scores: List[Dict[str, int]],
    persona_yamls: Dict[str, Dict[str, Any]],
    product_context: str = "",
    persona_outputs: Optional[List[Dict[str, Any]]] = None,
) -> List[PersonaEvaluation]:
    """Compute purchase intent for a batch of persona outputs."""
    results: List[PersonaEvaluation] = []
    outputs = persona_outputs or [{} for _ in range(len(all_rubric_scores))]

    for scores, output in zip(all_rubric_scores, outputs):
        persona_id = output.get("persona_id", "")
        yaml_data = persona_yamls.get(persona_id, {})
        results.append(
            compute_purchase_intent(scores, yaml_data, product_context, output)
        )

    return results
