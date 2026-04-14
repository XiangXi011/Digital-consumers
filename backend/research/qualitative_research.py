import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.domain.evidence_models import EvidenceAtom
from backend.infra.system_fingerprint import SCHEMA_VERSION, collect_system_fingerprint, collect_version_bundle
from backend.research.observability import compute_evaluation_metrics


SUMMARY_KEYS = [
    "consensus",
    "differences",
    "pain_points",
    "drivers",
    "barriers",
    "copy_insights",
    "recommendations",
]

STRUCTURED_RECOMMENDATION_KEYS = [
    "objective_answers",
    "cross_persona_consensus",
    "cross_persona_differences",
    "key_risks",
    "opportunity_areas",
    "recommended_actions",
    "copy_or_product_adjustments",
    "evidence_gaps",
    "confidence_assessment",
]

VALID_STANCES = {"interested", "hesitant", "rejecting"}

# Rubric score dimensions (1-5 discrete) - for product evaluation
# Default legacy dimensions; overridden per task_type via get_dimensions()
RUBRIC_DIMENSIONS = ["efficacy_clarity", "trust_signal", "convenience", "price_fit"]

# 5-Dimension persona framework - for persona description
PERSONA_FRAMEWORK_DIMENSIONS = [
    "identity_background",      # 身份背景
    "decision_preferences",     # 决策偏好
    "expression_style",         # 表达风格
    "behavior_constraints",     # 行为约束
    "traceable_evidence",       # 可追溯证据
]

# Default timeout for persona fan-out (seconds)
PERSONA_TIMEOUT_SECONDS = 60
PLANNER_RESPONSE_ATTEMPTS = 3
PERSONA_RESPONSE_ATTEMPTS = 4
SYNTHESIS_RESPONSE_ATTEMPTS = 5
DEFAULT_MULTI_PERSONA_IDS = [f"M0{index}" for index in range(1, 9)]
DEFAULT_EIGHT_MOM_PERSONA_PACK_ID = "default-eight-moms-v1"

# Sample pool: 25 samples per segment in persona_samples_complete.json
SAMPLES_PER_SEGMENT = 25


def select_random_persona_sample(
    persona_ids: List[str],
    samples_per_persona: int = 1,
    seed: Optional[int] = None,
) -> List[str]:
    """Randomly select persona IDs with representative sampling.

    For each persona in persona_ids, picks `samples_per_persona` indices
    from the 25-sample pool. Returns expanded persona IDs like "M01:3".

    Args:
        persona_ids: base persona IDs (e.g. ["M01", "M02"]).
        samples_per_persona: how many samples per persona (1 or 3 typical).
        seed: random seed for reproducibility.
    """
    rng = random.Random(seed)
    selected: List[str] = []
    for pid in persona_ids:
        indices = rng.sample(
            range(1, SAMPLES_PER_SEGMENT + 1),
            min(samples_per_persona, SAMPLES_PER_SEGMENT),
        )
        for idx in sorted(indices):
            selected.append(f"{pid}:{idx}")
    return selected

RESEARCH_PLAN_FIELD_ALIASES = {
    "research_objectives": ("research_goals", "objectives"),
    "sub_questions_for_personas": ("sub_questions",),
    "required_information": ("required_info", "required_inputs"),
    "missing_information": ("missing_info",),
    "clarifying_questions": ("clarification_questions",),
    "target_personas": ("selected_personas", "personas"),
    "planner_notes": ("notes",),
}

QUESTION_TYPE_EVALUATION_DEFAULTS = {
    "purchase_decision": ["trust", "value", "fit"],
    "copy_feedback": ["clarity", "trust", "appeal"],
    "product_concept": ["need", "clarity", "differentiation"],
    "concept_test": ["need", "clarity", "differentiation"],
    "packaging_review": ["shelf_impact", "clarity", "trust_signal"],
    "price_test": ["price", "value", "trust"],
    "ab_test": ["clarity", "appeal", "trust"],
}

QUESTION_TYPE_REQUIRED_INFORMATION_DEFAULTS = {
    "purchase_decision": ["user_question", "product_info_or_copy_material"],
    "copy_feedback": ["user_question", "copy_material"],
    "product_concept": ["user_question", "product_info"],
    "concept_test": ["user_question", "product_info"],
    "packaging_review": ["user_question", "product_info", "packaging_assets"],
    "price_test": ["user_question", "price_hypothesis"],
    "ab_test": ["user_question", "variant_a", "variant_b"],
}

QUESTION_TYPE_REQUIRED_PERSONA_FIELDS = {
    "concept_test": ["core_needs", "motivations", "concerns"],
    "packaging_review": ["concerns", "dimension_scores", "decision_logic"],
    "copy_feedback": ["task_responses", "dimension_scores", "verbatim_answer"],
    "ab_test": ["task_responses", "decision_logic", "what_would_change_my_mind"],
    "price_test": ["concerns", "decision_logic", "what_would_change_my_mind"],
}

logger = logging.getLogger(__name__)


class IncompleteResearchRunError(RuntimeError):
    pass


class ResearchPlannerBlockedError(RuntimeError):
    def __init__(self, research_plan: Dict[str, Any]):
        self.research_plan = research_plan
        missing = ", ".join(research_plan.get("missing_information", [])) or "unknown"
        questions = " ".join(research_plan.get("clarifying_questions", []))
        super().__init__(f"Planner blocked execution. Missing information: {missing}. {questions}".strip())


@dataclass
class QualitativeResearchInput:
    mode: str
    question_type: str
    user_question: str
    persona_id: str = ""
    background_material: str = ""
    product_info: str = ""
    copy_material: str = ""
    attachments: List[str] = field(default_factory=list)
    follow_up_context: str = ""
    persona_pack_id: str = ""
    audience_segments: List[str] = field(default_factory=list)
    enable_group_discussion: bool = False  # Layer 2: Group discussion
    enable_deep_dive: bool = False  # Layer 3: Deep dive


def _parse_json_object(text: str) -> Dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise IncompleteResearchRunError("LLM response text is empty.")

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise IncompleteResearchRunError("LLM response did not contain a JSON object.")

    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise IncompleteResearchRunError("LLM response JSON could not be parsed.") from exc


def _require_string(payload: Dict[str, Any], key: str, fallback: str = "") -> str:
    """Extract a string from payload, with optional fallback for more tolerant parsing."""
    value = payload.get(key)
    # Allow non-string values by converting them to strings
    if value is not None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        # Convert other types to string
        str_value = str(value).strip()
        if str_value:
            return str_value
    # Use fallback if provided
    if fallback:
        return fallback
    raise IncompleteResearchRunError(f"Missing or invalid string field: {key}")


def _require_string_list(
    payload: Dict[str, Any],
    key: str,
    *,
    allow_empty: bool = False,
    fallback: List[str] | None = None,
) -> List[str]:
    """Extract a string list from payload, with optional fallback for more tolerant parsing."""
    value = payload.get(key)
    if not isinstance(value, list):
        # If we have a single string, wrap it in a list
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        # Use fallback if provided
        if fallback is not None:
            return fallback
        if allow_empty:
            return []
        raise IncompleteResearchRunError(f"Missing or invalid list field: {key}")
    normalized = [str(item).strip() for item in value if str(item).strip()]
    if not normalized and not allow_empty:
        if fallback is not None:
            return fallback
        raise IncompleteResearchRunError(f"List field is empty: {key}")
    return normalized


def _require_bool(payload: Dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise IncompleteResearchRunError(f"Missing or invalid boolean field: {key}")
    return value


def _require_list_of_records(
    payload: Dict[str, Any],
    key: str,
    required_keys: List[str],
    *,
    fallback: List[Dict[str, str]] | None = None,
) -> List[Dict[str, str]]:
    """Extract a list of record dicts from payload, with optional fallback."""
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        if fallback is not None:
            return fallback
        raise IncompleteResearchRunError(f"Missing or invalid record list field: {key}")

    records: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            if fallback is not None:
                return fallback
            raise IncompleteResearchRunError(f"Invalid record item in field: {key}")
        normalized: Dict[str, str] = {}
        for required_key in required_keys:
            field_value = item.get(required_key)
            # Allow non-string values by converting them to strings
            if field_value is None:
                if fallback is not None:
                    return fallback
                raise IncompleteResearchRunError(
                    f"Missing or invalid record field: {key}.{required_key}"
                )
            normalized[required_key] = str(field_value).strip()
        records.append(normalized)
    return records


def _require_int_in_range(payload: Dict[str, Any], key: str, low: int = 1, high: int = 5) -> int:
    """Require an integer field within [low, high] range (for rubric scores)."""
    value = payload.get(key)
    if isinstance(value, float) and value == int(value):
        value = int(value)
    if not isinstance(value, int):
        raise IncompleteResearchRunError(f"Missing or invalid integer field: {key}")
    if value < low or value > high:
        raise IncompleteResearchRunError(f"Integer field {key} = {value} is out of range [{low}, {high}]")
    return value



def _coerce_string_list_value(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        flattened: List[str] = []
        for nested_value in value.values():
            nested_items = _coerce_string_list_value(nested_value) or []
            flattened.extend(nested_items)
        return flattened
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return None


def _coerce_bool_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return value


def _default_evaluation_dimensions(question_type: str) -> List[str]:
    return list(
        QUESTION_TYPE_EVALUATION_DEFAULTS.get(
            question_type,
            ["trust", "clarity", "fit"],
        )
    )


def _default_required_information(question_type: str) -> List[str]:
    return list(
        QUESTION_TYPE_REQUIRED_INFORMATION_DEFAULTS.get(
            question_type,
            ["user_question", "product_info_or_copy_material"],
        )
    )


def _infer_dispatch_scope(research_input: "QualitativeResearchInput") -> str:
    if research_input.mode in {"single", "multi"}:
        return research_input.mode
    if research_input.persona_id:
        return "single"
    return "multi"


def _uses_default_eight_mom_pack(research_input: "QualitativeResearchInput") -> bool:
    return (
        research_input.persona_pack_id == DEFAULT_EIGHT_MOM_PERSONA_PACK_ID
        and len(research_input.audience_segments) == len(DEFAULT_MULTI_PERSONA_IDS)
    )


def _normalize_target_persona_ids(
    target_personas: List[str],
    research_input: "QualitativeResearchInput",
    dispatch_scope: str,
) -> List[str]:
    normalized: List[str] = []
    for raw in target_personas:
        token = str(raw).strip()
        if not token:
            continue
        # Accept canonical ids directly
        if token in DEFAULT_MULTI_PERSONA_IDS:
            normalized.append(token)
            continue
        # Accept M1/M01/m01 forms
        match = re.search(r"\bM\s*0?([1-8])\b", token, flags=re.IGNORECASE)
        if match:
            normalized.append(f"M0{match.group(1)}")
            continue

    # single mode: fall back to explicit persona_id if available
    if dispatch_scope == "single":
        if normalized:
            return [normalized[0]]
        if research_input.persona_id and research_input.persona_id in DEFAULT_MULTI_PERSONA_IDS:
            return [research_input.persona_id]
        return [DEFAULT_MULTI_PERSONA_IDS[0]]

    # multi mode: if model produced non-canonical labels, fall back to default 8-pack
    deduped = list(dict.fromkeys(normalized))
    return deduped if deduped else list(DEFAULT_MULTI_PERSONA_IDS)


def _is_eight_mom_definition_gap(text: str) -> bool:
    normalized = (text or "").strip()
    if not normalized:
        return False
    if re.search(r"(?:8|八)\s*类妈妈", normalized):
        return True
    if "画像定义" in normalized:
        return True
    if "画像" in normalized and "定义" in normalized:
        return True
    if "细分" in normalized and ("人群" in normalized or "分类" in normalized):
        return True
    if "哪8类" in normalized or "哪八类" in normalized:
        return True
    return False


def _normalize_research_plan_payload(
    payload: Dict[str, Any],
    research_input: "QualitativeResearchInput",
) -> Dict[str, Any]:
    normalized = dict(payload)
    repairs: List[str] = []
    substantive_planner_field_count = sum(
        1
        for key in (
            "task_breakdown",
            "research_objectives",
            "evaluation_dimensions",
            "sub_questions_for_personas",
            "required_information",
            "missing_information",
            "clarifying_questions",
            "ready_to_dispatch",
            "dispatch_scope",
            "target_personas",
            "planner_notes",
        )
        if key in normalized and normalized.get(key) is not None
    )
    can_fill_structural_defaults = substantive_planner_field_count >= 4

    for canonical_field, aliases in RESEARCH_PLAN_FIELD_ALIASES.items():
        if canonical_field in normalized:
            continue
        for alias in aliases:
            if alias in payload:
                normalized[canonical_field] = payload[alias]
                repairs.append(f"{alias}->{canonical_field}")
                break

    for list_field in (
        "task_breakdown",
        "research_objectives",
        "evaluation_dimensions",
        "sub_questions_for_personas",
        "required_information",
        "missing_information",
        "clarifying_questions",
        "target_personas",
        "planner_notes",
    ):
        if list_field not in normalized:
            continue
        original_value = normalized.get(list_field)
        coerced_value = _coerce_string_list_value(original_value)
        if coerced_value is None:
            continue
        if not isinstance(original_value, list):
            normalized[list_field] = coerced_value
            repairs.append(f"scalar->{list_field}")

    task_breakdown = _coerce_string_list_value(normalized.get("task_breakdown")) or []
    if not task_breakdown and can_fill_structural_defaults:
        task_breakdown = [research_input.user_question]
        repairs.append("fallback->task_breakdown")
    normalized["task_breakdown"] = task_breakdown

    original_ready = normalized.get("ready_to_dispatch")
    coerced_ready = _coerce_bool_value(original_ready)
    if coerced_ready is not original_ready:
        normalized["ready_to_dispatch"] = coerced_ready
        repairs.append("coerced->ready_to_dispatch")

    research_objectives = _coerce_string_list_value(normalized.get("research_objectives")) or []
    if not research_objectives and can_fill_structural_defaults:
        research_objectives = list(task_breakdown) or [research_input.user_question]
        repairs.append("fallback->research_objectives")
    normalized["research_objectives"] = research_objectives

    evaluation_dimensions = _coerce_string_list_value(normalized.get("evaluation_dimensions")) or []
    if not evaluation_dimensions and can_fill_structural_defaults:
        evaluation_dimensions = _default_evaluation_dimensions(
            research_input.question_type
        )
        repairs.append("default->evaluation_dimensions")
    normalized["evaluation_dimensions"] = evaluation_dimensions

    sub_questions_for_personas = _coerce_string_list_value(
        normalized.get("sub_questions_for_personas")
    ) or []
    if not sub_questions_for_personas and can_fill_structural_defaults:
        sub_questions_for_personas = [research_input.user_question]
        repairs.append("default->sub_questions_for_personas")
    normalized["sub_questions_for_personas"] = sub_questions_for_personas

    required_information = _coerce_string_list_value(normalized.get("required_information")) or []
    if not required_information and can_fill_structural_defaults:
        required_information = _default_required_information(
            research_input.question_type
        )
        repairs.append("default->required_information")
    normalized["required_information"] = required_information

    if _coerce_string_list_value(normalized.get("missing_information")) is None and can_fill_structural_defaults:
        normalized["missing_information"] = []
        repairs.append("default->missing_information")
    else:
        normalized["missing_information"] = (
            _coerce_string_list_value(normalized.get("missing_information")) or []
        )

    ready_to_dispatch = normalized.get("ready_to_dispatch")
    if not isinstance(ready_to_dispatch, bool) and can_fill_structural_defaults:
        ready_to_dispatch = not bool(normalized.get("missing_information"))
        normalized["ready_to_dispatch"] = ready_to_dispatch
        repairs.append("derived->ready_to_dispatch")

    clarifying_questions = _coerce_string_list_value(normalized.get("clarifying_questions"))
    if clarifying_questions is None and can_fill_structural_defaults:
        if ready_to_dispatch:
            normalized["clarifying_questions"] = []
        else:
            missing_information = normalized.get("missing_information") or ["missing context"]
            normalized["clarifying_questions"] = [
                f"Please provide {missing_information[0]} so the study can start."
            ]
        repairs.append("default->clarifying_questions")
    else:
        normalized["clarifying_questions"] = clarifying_questions if clarifying_questions is not None else []

    if _uses_default_eight_mom_pack(research_input):
        filtered_required_information = [
            item
            for item in normalized["required_information"]
            if not _is_eight_mom_definition_gap(item)
        ]
        filtered_missing_information = [
            item
            for item in normalized["missing_information"]
            if not _is_eight_mom_definition_gap(item)
        ]
        filtered_clarifying_questions = [
            item
            for item in normalized["clarifying_questions"]
            if not _is_eight_mom_definition_gap(item)
        ]
        if filtered_required_information != normalized["required_information"]:
            normalized["required_information"] = filtered_required_information
            repairs.append("default_eight_moms->required_information")
        if filtered_missing_information != normalized["missing_information"]:
            normalized["missing_information"] = filtered_missing_information
            repairs.append("default_eight_moms->missing_information")
        if filtered_clarifying_questions != normalized["clarifying_questions"]:
            normalized["clarifying_questions"] = filtered_clarifying_questions
            repairs.append("default_eight_moms->clarifying_questions")
        if (
            normalized.get("ready_to_dispatch") is False
            and not normalized["missing_information"]
            and not normalized["clarifying_questions"]
        ):
            normalized["ready_to_dispatch"] = True
            repairs.append("default_eight_moms->ready_to_dispatch")

    dispatch_scope = normalized.get("dispatch_scope")
    if (
        not isinstance(dispatch_scope, str)
        or not dispatch_scope.strip()
        or dispatch_scope.strip() not in {"single", "multi"}
    ) and can_fill_structural_defaults:
        normalized["dispatch_scope"] = _infer_dispatch_scope(research_input)
        repairs.append("default->dispatch_scope")
    else:
        normalized["dispatch_scope"] = dispatch_scope.strip() if isinstance(dispatch_scope, str) else dispatch_scope

    target_personas = _coerce_string_list_value(normalized.get("target_personas")) or []
    if not target_personas and can_fill_structural_defaults:
        if normalized["dispatch_scope"] == "single":
            target_personas = [
                research_input.persona_id or DEFAULT_MULTI_PERSONA_IDS[0]
            ]
        else:
            target_personas = list(DEFAULT_MULTI_PERSONA_IDS)
        repairs.append("default->target_personas")

    normalized_target_personas = _normalize_target_persona_ids(
        target_personas,
        research_input,
        normalized["dispatch_scope"],
    )
    if normalized_target_personas != target_personas:
        repairs.append("normalize->target_personas")

    if (
        _uses_default_eight_mom_pack(research_input)
        and normalized["dispatch_scope"] == "multi"
        and any(persona_id not in DEFAULT_MULTI_PERSONA_IDS for persona_id in normalized_target_personas)
    ):
        normalized_target_personas = list(DEFAULT_MULTI_PERSONA_IDS)
        repairs.append("default_eight_moms->target_personas")

    normalized["target_personas"] = normalized_target_personas

    planner_notes = _coerce_string_list_value(normalized.get("planner_notes")) or []
    if repairs:
        planner_notes.append(
            "Planner output normalized to preserve the research-plan contract."
        )
    if not planner_notes:
        planner_notes = ["Planner output accepted without additional normalization."]
    normalized["planner_notes"] = planner_notes

    if repairs:
        logger.warning(
            "Normalized planner output for question_type=%s with repairs=%s",
            research_input.question_type,
            repairs,
        )

    return normalized


def _extract_rubric_scores(payload: Dict[str, Any], stance: str, task_type: str = "") -> Dict[str, int]:
    from backend.domain.scoring_registry import get_dimensions

    dimensions = get_dimensions(task_type) if task_type else RUBRIC_DIMENSIONS

    top_level_present = any(dim in payload for dim in dimensions)
    nested_scores = payload.get("rubric_scores")

    if top_level_present:
        return {
            dim: _require_int_in_range(payload, dim, 1, 5)
            for dim in dimensions
        }

    if isinstance(nested_scores, dict) and nested_scores:
        return {
            dim: _require_int_in_range(nested_scores, dim, 1, 5)
            for dim in dimensions
        }

    raise IncompleteResearchRunError(
        "Persona output must include explicit 1-5 rubric scores for all "
        f"dimensions ({', '.join(dimensions)}). "
        "Legacy stance-based fallback has been retired."
    )


def _validate_research_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    plan = {
        "task_breakdown": _require_string_list(payload, "task_breakdown"),
        "research_objectives": _require_string_list(payload, "research_objectives"),
        "evaluation_dimensions": _require_string_list(payload, "evaluation_dimensions"),
        "sub_questions_for_personas": _require_string_list(payload, "sub_questions_for_personas"),
        "required_information": _require_string_list(payload, "required_information"),
        "missing_information": _require_string_list(payload, "missing_information", allow_empty=True),
        "clarifying_questions": _require_string_list(payload, "clarifying_questions", allow_empty=True),
        "ready_to_dispatch": _require_bool(payload, "ready_to_dispatch"),
        "dispatch_scope": _require_string(payload, "dispatch_scope"),
        "target_personas": _require_string_list(payload, "target_personas"),
        "planner_notes": _require_string_list(payload, "planner_notes"),
    }

    if plan["dispatch_scope"] not in {"single", "multi"}:
        raise IncompleteResearchRunError("Invalid dispatch_scope in research plan.")
    if plan["dispatch_scope"] == "single" and len(plan["target_personas"]) != 1:
        raise IncompleteResearchRunError("Single-dispatch plan must target exactly one persona.")
    if not plan["ready_to_dispatch"] and not plan["clarifying_questions"]:
        raise IncompleteResearchRunError("Blocked research plan must include clarifying questions.")
    # 放宽条件：如果ready_to_dispatch为true，清空missing_information
    if plan["ready_to_dispatch"] and plan["missing_information"]:
        plan["missing_information"] = []

    return plan


def _enforce_explicit_user_scope(
    research_input: "QualitativeResearchInput",
    research_plan: Dict[str, Any],
) -> Dict[str, Any]:
    normalized_plan = dict(research_plan)
    normalized_plan["target_personas"] = list(research_plan.get("target_personas", []))
    normalized_plan["planner_notes"] = list(research_plan.get("planner_notes", []))

    if research_input.mode == "single" and research_input.persona_id:
        normalized_plan["dispatch_scope"] = "single"
        normalized_plan["target_personas"] = [research_input.persona_id]
        note = (
            f"Dispatch scope normalized to explicit user single-persona request: "
            f"{research_input.persona_id}."
        )
        if note not in normalized_plan["planner_notes"]:
            normalized_plan["planner_notes"].append(note)

    return normalized_plan


def _validate_mom_payload(
    payload: Dict[str, Any],
    expected_persona_id: str,
    question_type: str,
) -> Dict[str, Any]:
    persona_id = _require_string(payload, "persona_id")
    if persona_id != expected_persona_id:
        raise IncompleteResearchRunError(
            f"Persona mismatch: expected {expected_persona_id}, got {persona_id}."
        )

    stance = _require_string(payload, "stance")
    if stance not in VALID_STANCES:
        raise IncompleteResearchRunError(f"Invalid stance: {stance}")

    # Validate 1-5 rubric scores (math-decoupling: LLM emits only base scores)
    rubric_scores = _extract_rubric_scores(payload, stance, task_type=question_type)

    voice_line = str(payload.get("voice_line") or payload.get("verbatim_answer") or "").strip()
    confidence_note = str(
        payload.get("confidence_note") or payload.get("evidence_trace") or ""
    ).strip()
    triggered_veto_codes = payload.get("triggered_veto_codes", [])
    if triggered_veto_codes is None:
        triggered_veto_codes = []
    if not isinstance(triggered_veto_codes, list):
        raise IncompleteResearchRunError("Missing or invalid list field: triggered_veto_codes")
    normalized_veto_codes = [str(code).strip() for code in triggered_veto_codes if str(code).strip()]

    # Extract 5-dimension persona framework (optional, for enhanced output)
    persona_framework = {}
    for dim in PERSONA_FRAMEWORK_DIMENSIONS:
        dim_value = payload.get(dim)
        if dim_value:
            if isinstance(dim_value, dict):
                persona_framework[dim] = dim_value
            elif isinstance(dim_value, str) and dim_value.strip():
                persona_framework[dim] = {"description": dim_value.strip()}
            elif isinstance(dim_value, list):
                persona_framework[dim] = {"items": [str(item).strip() for item in dim_value if str(item).strip()]}

    result = {
        "persona_id": persona_id,
        "persona_name": _require_string(payload, "persona_name", fallback="未知"),
        "question_type": question_type,
        "rubric_scores": rubric_scores,
        "task_responses": _require_list_of_records(
            payload, "task_responses", ["question", "answer"],
            fallback=[{"question": "未提供", "answer": "未提供"}]
        ),
        "dimension_scores": _require_list_of_records(
            payload,
            "dimension_scores",
            ["dimension", "judgement"],
            fallback=[{"dimension": "综合", "judgement": "未提供详细评价"}],
        ),
        "stance": stance,
        "core_needs": _require_string_list(payload, "core_needs", fallback=["未提供"]),
        "motivations": _require_string_list(payload, "motivations", fallback=["未提供"]),
        "concerns": _require_string_list(payload, "concerns", fallback=["未提供"]),
        "decision_logic": _require_string(payload, "decision_logic", fallback="未提供"),
        "verbatim_answer": _require_string(payload, "verbatim_answer", fallback="未提供"),
        "voice_line": voice_line or _require_string(payload, "verbatim_answer", fallback="未提供"),
        "evidence_trace": _require_string(payload, "evidence_trace", fallback="未提供"),
        "confidence_note": confidence_note or _require_string(payload, "evidence_trace", fallback="未提供"),
        "triggered_veto_codes": normalized_veto_codes,
        "what_would_change_my_mind": str(
            payload.get("what_would_change_my_mind")
            or payload.get("decision_logic")
            or payload.get("verbatim_answer")
        ).strip(),
        "persona_framework": persona_framework,  # 5-dimension framework
    }

    required_fields = QUESTION_TYPE_REQUIRED_PERSONA_FIELDS.get(question_type, [])
    for field_name in required_fields:
        value = result.get(field_name)
        if isinstance(value, list) and not value:
            raise IncompleteResearchRunError(
                f"Missing required persona field for {question_type}: {field_name}"
            )
        if isinstance(value, str) and not value.strip():
            raise IncompleteResearchRunError(
                f"Missing required persona field for {question_type}: {field_name}"
            )

    # Enforce: persona must NOT emit weighted totals or purchase_intent
    for forbidden in ("purchase_score", "purchase_intent", "weighted_total", "final_score"):
        if forbidden in payload:
            raise IncompleteResearchRunError(
                f"Persona output must not contain '{forbidden}' — math must be decoupled to backend."
            )

    return result


def _validate_synthesis_payload(payload: Dict[str, Any], question_type: str = "") -> Dict[str, Any]:
    summary_payload = payload.get("research_summary")
    recommendation_payload = payload.get("structured_recommendation")
    if not isinstance(summary_payload, dict):
        raise IncompleteResearchRunError("Missing research_summary payload.")
    if not isinstance(recommendation_payload, dict):
        raise IncompleteResearchRunError("Missing structured_recommendation payload.")

    research_summary = {
        key: _require_string_list(summary_payload, key) for key in SUMMARY_KEYS
    }
    structured_recommendation = {
        key: _require_string_list(recommendation_payload, key)
        for key in STRUCTURED_RECOMMENDATION_KEYS
    }

    # Validate minority_reject_evidence preservation
    minority_evidence = payload.get("minority_reject_evidence")
    if minority_evidence is not None and isinstance(minority_evidence, list):
        structured_recommendation["minority_reject_evidence"] = minority_evidence

    if question_type == "ab_test":
        winner_signals = structured_recommendation.get("recommended_actions", [])
        if not winner_signals:
            raise IncompleteResearchRunError("AB test synthesis requires recommended_actions with winner guidance.")

    if question_type == "packaging_review":
        packaging_signals = research_summary.get("barriers", []) + research_summary.get("drivers", [])
        if not packaging_signals:
            raise IncompleteResearchRunError("Packaging review synthesis requires barriers/drivers evidence.")

    return {
        "research_summary": research_summary,
        "structured_recommendation": structured_recommendation,
    }


# ---------------------------------------------------------------------- #
#  Extract evidence atoms from persona outputs                            #
# ---------------------------------------------------------------------- #

def _extract_evidence_atoms(mom_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract structured evidence atoms from persona outputs.

    Per master-spec.md: RA must not synthesize directly from persona prose.
    First extract structured evidence atoms, then build consensus/divergence/
    minority-reject groupings from those atoms.
    """
    atoms: List[Dict[str, Any]] = []

    for output in mom_outputs:
        persona_id = output.get("persona_id", "")
        persona_name = output.get("persona_name", "")
        stance = output.get("stance", "")
        is_minority = stance == "rejecting"
        rubric_scores = output.get("rubric_scores", {})

        # Extract from concerns → evidence atoms
        for concern in output.get("concerns", []):
            field_type = _classify_evidence_field(concern)
            atoms.append(EvidenceAtom(
                agent_id=persona_id,
                persona_name=persona_name,
                field=field_type,
                value=concern,
                weight_hint=1.0,
                is_minority=is_minority,
            ).model_dump())

        # Extract from motivations → evidence atoms
        for motivation in output.get("motivations", []):
            field_type = _classify_evidence_field(motivation)
            atoms.append(EvidenceAtom(
                agent_id=persona_id,
                persona_name=persona_name,
                field=field_type,
                value=motivation,
                weight_hint=1.0,
                is_minority=False,
            ).model_dump())

        # Extract from core_needs → evidence atoms
        for need in output.get("core_needs", []):
            atoms.append(EvidenceAtom(
                agent_id=persona_id,
                persona_name=persona_name,
                field=_classify_evidence_field(need),
                value=need,
                weight_hint=0.8,
                is_minority=is_minority,
            ).model_dump())

        # Extract from rubric low scores as evidence of weakness
        for dim, score in rubric_scores.items():
            if isinstance(score, int) and score <= 2:
                atoms.append(EvidenceAtom(
                    agent_id=persona_id,
                    persona_name=persona_name,
                    field=_rubric_dim_to_evidence_field(dim),
                    value=f"{persona_name}给{dim}打了{score}分（满分5）",
                    weight_hint=1.5,
                    is_minority=is_minority,
                ).model_dump())

    return atoms


def _classify_evidence_field(text: str) -> str:
    """Classify a text snippet into an evidence field category.

    Uses word-boundary matching to avoid false positives like
    '副作用' matching '作用' or '成分不明' matching '成分'.
    """
    import re as _re
    # efficacy: positive evidence for product effectiveness
    if _re.search(r"(?:功效|效果|配方|成分|防蛀|清洁力|美白|清新口气|固齿)", text):
        return "efficacy"
    # trust: brand, authority, safety signals
    if _re.search(r"(?:信任|品牌|背书|安全|权威|医生|专业|可靠)", text):
        return "trust"
    # price: cost, value, budget
    if _re.search(r"(?:价格|贵|便宜|预算|性价比|划算|值)", text):
        return "price"
    # convenience: ease of use
    if _re.search(r"(?:方便|简单|操作|步骤|使用体验)", text):
        return "convenience"
    return "other"


def _rubric_dim_to_evidence_field(dim: str) -> str:
    """Map rubric dimension name to evidence field."""
    mapping = {
        # Legacy dimensions
        "efficacy_clarity": "efficacy",
        "trust_signal": "trust",
        "convenience": "convenience",
        "price_fit": "price",
        # concept_test / product_concept
        "demand_fit": "efficacy",
        "differentiation": "other",
        "purchase_drive": "other",
        "price_acceptance": "price",
        # packaging_review
        "shelf_recognition": "convenience",
        "info_clarity": "trust",
        "visual_trust": "trust",
        "pickup_willingness": "other",
        # copy_feedback
        "memory_strength": "efficacy",
        "credibility": "trust",
        "conversion_power": "other",
        "emotional_resonance": "other",
        # ab_test
        "option_a_alignment": "other",
        "option_b_alignment": "other",
        "overall_preference": "other",
        "switching_cost": "other",
        # price_test
        "price_sensitivity": "price",
        "value_perception": "price",
        "competitive_position": "price",
        "purchase_willingness": "other",
    }
    return mapping.get(dim, "other")


def _extract_winner_signals(mom_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract A/B test winner signals from persona evaluations."""
    signals = []
    for output in mom_outputs:
        eval_data = output.get("backend_evaluation", {})
        ws = eval_data.get("winner_signal")
        if ws is not None:
            signals.append({
                "persona_id": output.get("persona_id", ""),
                "persona_name": output.get("persona_name", ""),
                "winner_signal": ws,
                "direction": "A wins" if ws > 0 else ("B wins" if ws < 0 else "tie"),
            })
    return signals


def _group_evidence_atoms(atoms: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group evidence atoms into consensus, divergence, and minority-reject.

    Consensus is defined per-field: if majority atoms come from >= 2 distinct
    personas AND represent > 50% of all atoms in that field, they are consensus.
    This adapts to different group sizes (3-persona tests or 8-persona production).
    """
    consensus = []
    divergence = []
    minority_reject = []

    field_values: Dict[str, List[Dict[str, Any]]] = {}
    for atom in atoms:
        field_values.setdefault(atom["field"], []).append(atom)

    for field_key, field_atoms in field_values.items():
        minority_atoms = [a for a in field_atoms if a["is_minority"]]
        majority_atoms = [a for a in field_atoms if not a["is_minority"]]

        if minority_atoms:
            minority_reject.extend(minority_atoms)

        # Count distinct personas in majority
        majority_persona_ids = {a.get("agent_id", "") for a in majority_atoms}
        total_field_atoms = len(field_atoms)

        # Consensus: at least 2 majority personas AND majority > 50% of total
        if len(majority_persona_ids) >= 2 and len(majority_atoms) > total_field_atoms * 0.5:
            consensus.extend(majority_atoms[:3])
        elif majority_atoms:
            divergence.extend(majority_atoms)

    return {
        "top_consensus_evidence": consensus,
        "top_divergence_evidence": divergence,
        "minority_reject_evidence": minority_reject,
    }


class ResearchPlannerAgent:
    PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "")

    def __init__(self, ai_client: Any):
        self.ai_client = ai_client

    def run(self, research_input: QualitativeResearchInput) -> Dict[str, Any]:
        prompt = self._prompt(research_input)
        result: Dict[str, Any] | None = None
        last_errors: List[str] = []
        last_parse_error: IncompleteResearchRunError | None = None
        for attempt in range(PLANNER_RESPONSE_ATTEMPTS):
            _kwargs: Dict[str, Any] = dict(
                prompt=prompt,
                system_prompt="You are a research planner agent. Return strict JSON only.",
            )
            if self.PLANNER_MODEL:
                _kwargs["model"] = self.PLANNER_MODEL
            result = self.ai_client.generate_text(**_kwargs)
            if result.get("mode") != "live_text":
                last_errors = [str(item) for item in result.get("errors", []) if str(item).strip()]
                logger.warning(
                    "Planner returned non-live mode on attempt %s/%s for question_type=%s. mode=%s errors=%s",
                    attempt + 1,
                    PLANNER_RESPONSE_ATTEMPTS,
                    research_input.question_type,
                    result.get("mode"),
                    last_errors,
                )
                continue

            raw_text = (result or {}).get("text", "")
            try:
                payload = _parse_json_object(raw_text)
            except IncompleteResearchRunError as exc:
                last_parse_error = exc
                logger.warning(
                    "Planner JSON parse failed on attempt %s/%s for question_type=%s. raw_preview=%r",
                    attempt + 1,
                    PLANNER_RESPONSE_ATTEMPTS,
                    research_input.question_type,
                    raw_text[:400],
                )
                continue

            normalized_payload = _normalize_research_plan_payload(payload, research_input)
            try:
                return _validate_research_plan(normalized_payload)
            except IncompleteResearchRunError as exc:
                last_parse_error = exc
                logger.warning(
                    "Planner output invalid after normalization on attempt %s/%s for question_type=%s. "
                    "raw_keys=%s normalized_keys=%s",
                    attempt + 1,
                    PLANNER_RESPONSE_ATTEMPTS,
                    research_input.question_type,
                    sorted(payload.keys()),
                    sorted(normalized_payload.keys()),
                )
                continue

        # All attempts exhausted — use fallback
        logger.error(
            "Planner exhausted retries for question_type=%s. last_mode=%s errors=%s last_parse_error=%s",
            research_input.question_type,
            (result or {}).get("mode"),
            last_errors,
            last_parse_error,
        )
        logger.warning(
            "Using fallback planner payload due to upstream planner failure. question_type=%s",
            research_input.question_type,
        )
        payload = {
            "task_breakdown": [research_input.user_question or "这款产品怎么样？"],
            "research_objectives": [research_input.user_question or "评估产品概念可行性"],
            "evaluation_dimensions": _default_evaluation_dimensions(research_input.question_type),
            "sub_questions_for_personas": [research_input.user_question or "请给出你的真实购买判断"],
            "required_information": _default_required_information(research_input.question_type),
            "missing_information": [],
            "clarifying_questions": ["请检查 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL 配置"],
            "ready_to_dispatch": False,
            "dispatch_scope": _infer_dispatch_scope(research_input),
            "target_personas": [research_input.persona_id] if research_input.mode == "single" and research_input.persona_id else list(DEFAULT_MULTI_PERSONA_IDS),
            "planner_notes": [
                "Planner fallback plan generated due to upstream LLM authentication or availability issue.",
                "建议检查 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL 配置。",
            ],
        }
        normalized_payload = _normalize_research_plan_payload(payload, research_input)
        return _validate_research_plan(normalized_payload)

    def _prompt(self, research_input: QualitativeResearchInput) -> str:
        # 自动补充默认值，降低业务人员输入门槛
        product_info = research_input.product_info or "（用户提供产品信息）"
        user_question = research_input.user_question or "这款产品怎么样？"

        flow_instructions = {
            "concept_test": "你是概念评审 Agent：聚焦需求匹配、差异化、购买驱动力。",
            "packaging_review": "你是包装评审 Agent：聚焦货架识别、包装信息清晰度、视觉信任感、开箱/携带体验。",
            "copy_feedback": "你是文案评审 Agent：聚焦文案清晰度、说服力、可信度与行动驱动。",
            "ab_test": "你是A/B评审 Agent：必须明确比较A/B差异并给出推荐版本与理由。",
            "price_test": "你是价格评审 Agent：聚焦价格接受度、心理锚点和替代品比较。",
        }
        flow_hint = flow_instructions.get(research_input.question_type, "你是市场研究助手，返回 JSON。")

        return "\n".join(
            [
                flow_hint,
                "",
                "【核心原则】让业务人员用最少的信息就能启动测试",
                "",
                "【判断规则】",
                "1. 只要有产品信息（名称、价格、核心卖点之一）就可以发起调研",
                "2. 用户问题可以模糊，系统会自动补充",
                "3. 画像ID存在就可以，背景信息系统会自动补充",
                "4. 不要要求用户提供调研方法、样本量、预算等专业信息",
                "5. 缺失的非关键信息用合理默认值填充，不要阻塞流程",
                "",
                "【自动填充规则】",
                "- 如果 product_info 缺失，用'用户提供产品信息'并继续",
                "- 如果 user_question 缺失，用'这款产品怎么样？'",
                "- 如果 dispatch_scope 缺失，默认为 single",
                "- 如果 target_personas 缺失，根据 persona_id 填充",
                "- 如果 evaluation_dimensions 缺失，根据 question_type 自动选择",
                "",
                f"用户问题类型: {research_input.question_type}",
                f"用户问题: {user_question}",
                f"用户要求模式: {research_input.mode}",
                f"指定画像: {research_input.persona_id}",
                f"画像包标识: {research_input.persona_pack_id}",
                f"细分人群定义: {json.dumps(research_input.audience_segments, ensure_ascii=False)}",
                f"产品信息: {product_info}",
                f"文案/卖点: {research_input.copy_material}",
                f"背景资料: {research_input.background_material}",
                f"追问上下文: {research_input.follow_up_context}",
                f"附件: {json.dumps(research_input.attachments, ensure_ascii=False)}",
                "",
                "【JSON格式】返回以下字段：",
                "- task_breakdown: 任务拆解（数组）",
                "- research_objectives: 研究目标（数组）",
                "- evaluation_dimensions: 评估维度（数组，根据question_type自动选择）",
                "- sub_questions_for_personas: 子问题（数组）",
                "- required_information: 需要的信息（数组）",
                "- missing_information: 缺失信息（数组，应该很少）",
                "- clarifying_questions: 澄清问题（数组，应该很少）",
                "- ready_to_dispatch: true/false（通常应该为true）",
                "- dispatch_scope: single/multi",
                "- target_personas: 目标画像ID（数组）",
                "- planner_notes: 规划备注（数组）",
            ]
        )


class MomPersonaAgent:
    def __init__(self, persona: Dict[str, Any], ai_client: Any, persona_yaml: Optional[Dict[str, Any]] = None):
        self.persona = persona
        self.ai_client = ai_client
        self.persona_yaml = persona_yaml or {}

    def run(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        validated = None
        last_error: IncompleteResearchRunError | None = None
        for attempt in range(PERSONA_RESPONSE_ATTEMPTS):
            try:
                result = self.ai_client.generate_text(
                    prompt=self._prompt(research_input, research_plan),
                    system_prompt=(
                        "You are speaking as one specific Chinese mother consumer persona. "
                        "You must output ONLY discrete 1-5 rubric scores for each dimension. "
                        "Do NOT output any weighted totals, purchase scores, or purchase intent. "
                        "Return strict JSON only."
                    ),
                )
            except AssertionError as exc:
                if last_error is not None:
                    raise last_error from exc
                raise
            if result.get("mode") != "live_text":
                last_error = IncompleteResearchRunError(
                    "Mother agent did not complete with a live LLM response."
                )
                logger.warning(
                    "Persona agent returned non-live mode on attempt %s/%s for persona_id=%s question_type=%s. mode=%s errors=%s",
                    attempt + 1,
                    PERSONA_RESPONSE_ATTEMPTS,
                    self.persona["segment_id"],
                    research_input.question_type,
                    result.get("mode"),
                    [str(item) for item in result.get("errors", []) if str(item).strip()],
                )
                if attempt + 1 >= PERSONA_RESPONSE_ATTEMPTS:
                    raise last_error
                continue

            try:
                payload = _parse_json_object(result.get("text", ""))
                validated = _validate_mom_payload(
                    payload,
                    expected_persona_id=self.persona["segment_id"],
                    question_type=research_input.question_type,
                )
                break
            except IncompleteResearchRunError as exc:
                last_error = exc
                if attempt + 1 >= PERSONA_RESPONSE_ATTEMPTS:
                    raise
                # Retry on JSON parse failures and persona mismatch
                if "Persona mismatch" in str(exc):
                    logger.warning(
                        "Persona mismatch on attempt %s/%s, retrying...",
                        attempt + 1, PERSONA_RESPONSE_ATTEMPTS,
                    )
                else:
                    logger.warning(
                        "Persona JSON parse/validation failed on attempt %s/%s, retrying. error=%s",
                        attempt + 1, PERSONA_RESPONSE_ATTEMPTS, exc,
                    )
                continue

        # Backend scoring: compute purchase intent from rubric scores
        # (math-decoupling: scoring happens here, not in LLM)
        try:
            from backend.domain.persona_scoring import compute_purchase_intent

            evaluation = compute_purchase_intent(
                rubric_scores=validated["rubric_scores"],
                persona_yaml=self.persona_yaml,
                product_context=research_input.product_info,
                persona_output=validated,
                task_type=research_input.question_type,
            )
            validated["backend_evaluation"] = evaluation.model_dump()
        except Exception as exc:
            # Log scoring failure but continue - report will show empty backend evaluation
            logger.warning(
                "Backend scoring failed for persona %s: %s",
                self.persona.get("segment_id", "unknown"),
                exc,
                exc_info=True,
            )
            validated["backend_evaluation"] = {"_scoring_failed": True, "_error": str(exc)}

        return validated

    def _prompt(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> str:
        basic_profile = self.persona.get("basic_profile", {})
        consumption_profile = self.persona.get("consumption_profile", {})
        mindset_profile = self.persona.get("mindset_profile", {})
        behavior_profile = self.persona.get("behavior_profile", {})
        expression_profile = self.persona.get("expression_profile", {})

        # Build rubric text from persona YAML if available
        rubric_text = ""
        rubric = self.persona_yaml.get("feature_scoring_rubric", {})
        if rubric:
            rubric_lines = ["", "评分标准（每个维度1-5分）："]
            for dim_name, levels in rubric.items():
                rubric_lines.append(f"  {dim_name}:")
                for score, desc in sorted(levels.items(), reverse=True):
                    rubric_lines.append(f"    {score}分: {desc}")
            rubric_text = "\n".join(rubric_lines)

        veto_text = ""
        veto_trigger = self.persona_yaml.get("veto_trigger", "")
        if veto_trigger:
            veto_text = f"\n你的一票否决条件: {veto_trigger}"

        # 提取详细人设信息
        nickname = basic_profile.get('nickname', self.persona['segment_name'])
        age = basic_profile.get('age', '未知')
        city = basic_profile.get('city', '未知')
        city_tier = basic_profile.get('city_tier', '未知')
        occupation = basic_profile.get('occupation', '未知')
        income = basic_profile.get('household_income_band', '未知')
        child_age = basic_profile.get('child_age_stage', '未知')
        child_gender = basic_profile.get('child_gender', '未知')
        family_structure = basic_profile.get('family_structure', '未知')
        
        core_needs = consumption_profile.get('core_needs', [])
        preferred_channels = consumption_profile.get('preferred_channels', [])
        trust_trigger = consumption_profile.get('trust_trigger', '')
        rejection_trigger = consumption_profile.get('rejection_trigger', '')
        budget_range = consumption_profile.get('budget_range', '')
        
        decision_mode = mindset_profile.get('decision_mode', '')
        openness = mindset_profile.get('openness_level', '')
        price_sensitivity = mindset_profile.get('price_sensitivity', '')
        evidence_sensitivity = mindset_profile.get('evidence_sensitivity', '')
        
        content_habit = behavior_profile.get('content_habit', '')
        decision_style = behavior_profile.get('decision_style', '')
        family_role = behavior_profile.get('family_role', '')
        
        tone_style = expression_profile.get('tone_style', '')
        likely_quote = expression_profile.get('likely_quote', '')

        mode_specific_guidance = {
            "concept_test": [
                "【本轮任务重点：概念评审】",
                "- 明确你是否理解产品概念，以及是否能解决真实需求",
                "- 重点评价差异化和购买驱动力",
            ],
            "packaging_review": [
                "【本轮任务重点：包装评审】",
                "- 重点评价包装第一眼识别、信息清晰度、视觉信任感",
                "- 说明包装文案/元素中让你困惑或增强信任的具体点",
            ],
            "copy_feedback": [
                "【本轮任务重点：文案评审】",
                "- 重点评价文案是否清晰、可信、打动你并促使行动",
                "- 指出最有说服力与最反感的句子",
            ],
            "ab_test": [
                "【本轮任务重点：A/B评审】",
                "- 必须对比A/B版本并明确你的倾向",
                "- 给出选择理由和触发改变选择的条件",
            ],
            "price_test": [
                "【本轮任务重点：价格评审】",
                "- 明确该价格是否在你可接受区间内",
                "- 说明心理价位、比较对象和降价/增值触发条件",
            ],
        }.get(research_input.question_type, [])

        from backend.domain.scoring_registry import get_dimensions
        dimensions = get_dimensions(research_input.question_type)

        return "\n".join(
            [
                f"你是{nickname}，一个{city}{city_tier}的{occupation}。",
                "你需要用消费者的真实语言回答，不要用专家或策略师的口吻。",
                "",
                "【重要】persona_id 必须是 " + self.persona['segment_id'] + "，不要改变！",
                "",
                "【你的真实身份】",
                f"- 年龄：{age}岁",
                f"- 职业：{occupation}",
                f"- 家庭：{family_structure}，孩子{child_age}{child_gender}",
                f"- 收入：{income}",
                f"- 城市：{city}（{city_tier}）",
                "",
                "【你的消费特征】",
                f"- 核心需求：{', '.join(core_needs)}",
                f"- 购买渠道：{', '.join(preferred_channels)}",
                f"- 预算范围：{budget_range}",
                f"- 信任触发：{trust_trigger}",
                f"- 拒绝触发：{rejection_trigger}",
                "",
                "【你的决策方式】",
                f"- 决策模式：{decision_mode}",
                f"- 开放度：{openness}",
                f"- 价格敏感度：{price_sensitivity}",
                f"- 证据敏感度：{evidence_sensitivity}",
                f"- 内容习惯：{content_habit}",
                f"- 决策风格：{decision_style}",
                f"- 家庭角色：{family_role}",
                "",
                "【你的表达风格】",
                f"- 语气：{tone_style}",
                f"- 典型话术：{likely_quote}",
                veto_text,
                rubric_text,
                "",
                *mode_specific_guidance,
                "",
                "【研究任务卡】",
                json.dumps(research_plan, ensure_ascii=False, indent=2),
                "",
                "【JSON输出格式】",
                "返回以下字段：",
                "- persona_id: 你的画像ID",
                "- persona_name: 你的昵称",
                "- stance: interested/hesitant/rejecting",
                f"- rubric_scores: {{{': 1-5, '.join(dimensions)}: 1-5}}",
                "- task_responses: [{question, answer}]",
                "- dimension_scores: [{dimension, judgement}]",
                "- core_needs: 核心需求列表",
                "- motivations: 购买动机列表",
                "- concerns: 顾虑列表",
                "- decision_logic: 决策逻辑（一段话）",
                "- verbatim_answer: 你的原话回答",
                "- evidence_trace: 你的判断依据",
                "",
                "【评分解释（重要！）",
                "每个评分维度必须给出解释，格式：",
                *[f"- {dim}_score: X分，因为..." for dim in dimensions],
                "",
                "【决策逻辑说明（重要！）",
                "在 decision_logic 中详细说明：",
                "1. 你会买/不会买的核心原因",
                "2. 哪些因素影响了你的决定",
                "3. 什么情况会改变你的决定",
                "",
                f"研究问题类型: {research_input.question_type}",
                f"用户问题: {research_input.user_question}",
                f"产品信息: {research_input.product_info}",
                f"文案/卖点: {research_input.copy_material}",
                f"背景资料: {research_input.background_material}",
            ]
        )


class ResearchSynthesizerAgent:
    """RA synthesizer — evidence-grounded per master-spec.md.

    Must not synthesize directly from persona prose. First extracts structured
    evidence atoms, then builds consensus/divergence/minority-reject groupings.
    """

    def __init__(self, ai_client: Any):
        self.ai_client = ai_client

    def run(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
        mom_outputs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Step 1: Extract evidence atoms from persona outputs
        evidence_atoms = _extract_evidence_atoms(mom_outputs)
        evidence_groups = _group_evidence_atoms(evidence_atoms)

        # Extract winner signals for A/B tests
        winner_signals = _extract_winner_signals(mom_outputs)

        # Step 2: Synthesize from evidence atoms (not raw persona prose)
        synthesis = None
        last_error: IncompleteResearchRunError | None = None
        for attempt in range(SYNTHESIS_RESPONSE_ATTEMPTS):
            try:
                result = self.ai_client.generate_text(
                    prompt=self._prompt(research_input, research_plan, evidence_groups, winner_signals),
                    system_prompt=(
                        "You are a qualitative research synthesizer. Return strict JSON only. "
                        "You must cite specific evidence atoms in your synthesis. "
                        "You must preserve minority rejection reasons in the output."
                    ),
                )
            except AssertionError as exc:
                if last_error is not None:
                    raise last_error from exc
                raise
            if result.get("mode") != "live_text":
                last_error = IncompleteResearchRunError(
                    "Research synthesizer did not complete with a live LLM response."
                )
                logger.warning(
                    "Synthesizer returned non-live mode on attempt %s/%s for question_type=%s. mode=%s errors=%s",
                    attempt + 1,
                    SYNTHESIS_RESPONSE_ATTEMPTS,
                    research_input.question_type,
                    result.get("mode"),
                    [str(item) for item in result.get("errors", []) if str(item).strip()],
                )
                if attempt + 1 >= SYNTHESIS_RESPONSE_ATTEMPTS:
                    raise last_error
                continue

            try:
                payload = _parse_json_object(result.get("text", ""))
                synthesis = _validate_synthesis_payload(payload, research_input.question_type)
                break
            except IncompleteResearchRunError as exc:
                last_error = exc
                logger.warning(
                    "Synthesizer JSON parse/validation failed on attempt %s/%s for question_type=%s. error=%s",
                    attempt + 1, SYNTHESIS_RESPONSE_ATTEMPTS, research_input.question_type, exc,
                )
                if attempt + 1 >= SYNTHESIS_RESPONSE_ATTEMPTS:
                    raise
                continue

        # Attach evidence metadata to synthesis
        synthesis["evidence_atoms"] = evidence_atoms
        synthesis["evidence_groups"] = evidence_groups

        return synthesis

    def _prompt(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
        evidence_groups: Dict[str, List[Dict[str, Any]]],
        winner_signals: List[Dict[str, Any]] | None = None,
    ) -> str:
        synthesis_focus = {
            "concept_test": "Focus on need-solution fit, differentiation, and purchase drivers.",
            "packaging_review": "Focus on shelf impact, packaging clarity, trust signals, and usability concerns.",
            "copy_feedback": "Focus on copy clarity, persuasion, credibility, and action trigger quality.",
            "ab_test": "Focus on A/B winner decision, key evidence for each side, and recommendation confidence.",
            "price_test": "Focus on price acceptability, anchor effects, and price elasticity signals.",
        }.get(research_input.question_type, "Focus on evidence-based synthesis and preserve minority views.")

        lines = [
            "You are a qualitative research synthesizer. Return JSON only.",
            "The output must contain research_summary and structured_recommendation.",
            f"research_summary keys: {', '.join(SUMMARY_KEYS)}",
            f"structured_recommendation keys: {', '.join(STRUCTURED_RECOMMENDATION_KEYS)}",
            "",
            "Rules:",
            "1. Base every conclusion on the structured evidence below.",
            "2. Preserve minority rejection reasons.",
            "3. Cite which persona each evidence atom came from.",
            "",
            f"mode_focus: {synthesis_focus}",
            f"question_type: {research_input.question_type}",
            f"user_question: {research_input.user_question}",
            "research_plan:",
            json.dumps(research_plan, ensure_ascii=False, indent=2),
            "",
            "top_consensus_evidence:",
            json.dumps(evidence_groups.get("top_consensus_evidence", []), ensure_ascii=False, indent=2),
            "",
            "top_divergence_evidence:",
            json.dumps(evidence_groups.get("top_divergence_evidence", []), ensure_ascii=False, indent=2),
            "",
            "minority_reject_evidence:",
            json.dumps(evidence_groups.get("minority_reject_evidence", []), ensure_ascii=False, indent=2),
        ]

        if winner_signals:
            lines.extend([
                "",
                "A/B winner_signals (positive=A wins, negative=B wins):",
                json.dumps(winner_signals, ensure_ascii=False, indent=2),
            ])

        return "\n".join(lines)


class QualitativeResearchRunner:
    def __init__(self, persona_path: Path | str, ai_client: Any | None = None):
        self.persona_path = Path(persona_path)
        self.ai_client = ai_client
        self.personas = self._load_personas()
        self.persona_yamls = self._load_persona_yamls()

    def plan(self, research_input: QualitativeResearchInput) -> Dict[str, Any]:
        self._ensure_ai_client()
        return _enforce_explicit_user_scope(
            research_input,
            ResearchPlannerAgent(self.ai_client).run(research_input),
        )

    def run(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Run the three-layer qualitative research process.

        Layer 1: Initial persona evaluation (8 representatives)
        Layer 2: Group discussion among selected personas (optional)
        Layer 3: Deep dive with key personas (optional)
        """
        self._ensure_ai_client()
        pipeline_started_at = time.perf_counter()
        research_plan = _enforce_explicit_user_scope(
            research_input,
            research_plan or self.plan(research_input),
        )
        if not research_plan["ready_to_dispatch"]:
            raise ResearchPlannerBlockedError(research_plan)

        selected_personas = self._select_personas_from_plan(research_plan)

        # Phase 3: Analyze image attachments with vision model
        image_analyses = self._analyze_image_attachments(research_input)
        if image_analyses:
            research_input.background_material = (
                research_input.background_material
                + "\n\n【图片附件分析】\n"
                + "\n".join(f"- {a['filename']}: {a['description']}" for a in image_analyses)
            )

        # Layer 1: Run initial persona evaluation
        consumer_voice = self._run_personas_concurrent(
            selected_personas, research_input, research_plan
        )

        # Layer 2: Group discussion — explicit flag OR auto-trigger on high divergence
        group_discussion = None
        should_discuss = research_input.enable_group_discussion
        if not should_discuss and research_input.mode == "multi" and len(consumer_voice) >= 3:
            divergence = self._compute_divergence_score(consumer_voice)
            if divergence > 0.5:
                should_discuss = True
                logger.info("Auto-triggering group discussion: divergence_score=%.2f", divergence)
        if should_discuss and research_input.mode == "multi" and len(consumer_voice) >= 2:
            group_discussion = self._run_group_discussion(
                consumer_voice, research_input, research_plan
            )

        # Layer 3: Deep dive — explicit flag OR auto-trigger on unresolved issues
        deep_dive_results = None
        should_deep_dive = research_input.enable_deep_dive
        if not should_deep_dive and group_discussion and group_discussion.get("status") == "completed":
            if group_discussion.get("unresolved_issues"):
                should_deep_dive = True
                logger.info("Auto-triggering deep dive: %d unresolved issues", len(group_discussion["unresolved_issues"]))
        if should_deep_dive and group_discussion:
            deep_dive_results = self._run_deep_dive(
                consumer_voice, group_discussion, research_input, research_plan
            )

        synthesis = ResearchSynthesizerAgent(self.ai_client).run(
            research_input,
            research_plan,
            consumer_voice,
        )
        pipeline_total_latency_ms = round((time.perf_counter() - pipeline_started_at) * 1000, 2)

        # Phase 3: record pipeline metrics
        try:
            from backend.infra.metrics import record_pipeline_duration
            record_pipeline_duration(pipeline_total_latency_ms / 1000.0)
        except Exception:
            pass

        report_mode = research_plan["dispatch_scope"]
        selected_persona = (
            research_plan["target_personas"][0] if report_mode == "single" else None
        )
        base_dir = self.persona_path.resolve().parent

        report = {
            "meta": {
                "mode": report_mode,
                "question_type": research_input.question_type,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_agents": len(consumer_voice),
                "agent_count_expected": len(selected_personas),
                "agent_count_completed": len(consumer_voice),
                "completion_status": "complete" if len(consumer_voice) == len(selected_personas) else "partial",
                "schema_version": SCHEMA_VERSION,
                "system_fingerprint": collect_system_fingerprint(
                    base_dir,
                    ai_client=self.ai_client,
                ),
                "version_bundle": collect_version_bundle(
                    base_dir,
                    ai_client=self.ai_client,
                ),
                "pipeline_total_latency_ms": pipeline_total_latency_ms,
            },
            "research_brief": {
                "user_question": research_input.user_question,
                "product_info": research_input.product_info,
                "copy_material": research_input.copy_material,
                "background_material": research_input.background_material,
            },
            "research_plan": research_plan,
            "consumer_voice": consumer_voice,
            "group_discussion": group_discussion,
            "deep_dive_results": deep_dive_results,
            "evidence_atoms": synthesis.get("evidence_atoms", []),
            "evidence_groups": synthesis.get("evidence_groups", {}),
            "research_summary": synthesis["research_summary"],
            "structured_recommendation": synthesis["structured_recommendation"],
            "appendix": {
                "selected_persona": selected_persona,
                "follow_up_context": research_input.follow_up_context,
                "attachments": list(research_input.attachments),
                "input_snapshot_summary": {
                    "user_question": research_input.user_question,
                    "product_info": research_input.product_info,
                    "copy_material": research_input.copy_material,
                    "dispatch_scope": research_plan["dispatch_scope"],
                    "target_personas": list(research_plan["target_personas"]),
                },
            },
        }
        report["meta"]["evaluation_metrics"] = compute_evaluation_metrics(report)

        return report

    def _analyze_image_attachments(
        self,
        research_input: QualitativeResearchInput,
    ) -> List[Dict[str, Any]]:
        """Analyze image attachments using vision model for richer persona prompts."""
        from backend.infra.media_processor import is_image_file, validate_image

        analyses: List[Dict[str, Any]] = []
        for attachment in research_input.attachments:
            att_path = Path(attachment)
            if not att_path.is_absolute():
                # Try relative to common output dirs
                for base in [Path("outputs"), Path("."), self.persona_path.parent]:
                    candidate = base / attachment
                    if candidate.exists():
                        att_path = candidate
                        break

            if not att_path.exists() or not is_image_file(att_path):
                continue

            validation = validate_image(att_path)
            if not validation.get("valid"):
                logger.warning("Skipping invalid image %s: %s", attachment, validation.get("error"))
                continue

            try:
                vision_result = self.ai_client.analyze_image(
                    att_path,
                    prompt="请详细描述这张产品图片的内容，包括：1) 产品外观和包装 2) 文字信息 3) 色彩和设计元素 4) 可能的目标消费者感知",
                )
                description = vision_result.get("text", "")
                if description and vision_result.get("mode") != "fallback_vision":
                    analyses.append({
                        "filename": att_path.name,
                        "description": description[:500],
                        "model": vision_result.get("model", ""),
                    })
            except Exception as exc:
                logger.warning("Image analysis failed for %s: %s", attachment, exc)

        return analyses

    def _select_discussion_participants(
        self,
        consumer_voice: List[Dict[str, Any]],
        max_participants: int = 4,
    ) -> List[Dict[str, Any]]:
        """Select diverse participants for group discussion.

        Strategy: pick representatives from each stance category (rejecting/neutral/interested)
        to maximize viewpoint diversity, then fill remaining slots randomly.
        """
        if len(consumer_voice) <= max_participants:
            return list(consumer_voice)

        by_stance: Dict[str, List[Dict[str, Any]]] = {}
        for voice in consumer_voice:
            stance = voice.get("stance", "neutral")
            by_stance.setdefault(stance, []).append(voice)

        selected: List[Dict[str, Any]] = []
        # One from each stance, prioritizing extremes
        for stance in ["rejecting", "interested", "neutral", "supportive"]:
            pool = by_stance.get(stance, [])
            if pool and len(selected) < max_participants:
                selected.append(random.choice(pool))

        # Fill remaining slots from unselected
        selected_names = {p.get("persona_name") for p in selected}
        remaining = [v for v in consumer_voice if v.get("persona_name") not in selected_names]
        random.shuffle(remaining)
        while len(selected) < max_participants and remaining:
            selected.append(remaining.pop())

        return selected

    def _run_group_discussion(
        self,
        consumer_voice: List[Dict[str, Any]],
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Layer 2: Structured multi-round group discussion.

        Simulates a 3-round focus group:
          Round 1 — Each participant states their position
          Round 2 — Cross-reactions to differing viewpoints
          Round 3 — Attempt to reach consensus or identify irreconcilable differences
        """
        if len(consumer_voice) < 2:
            return {"status": "skipped", "reason": "Not enough personas for discussion"}

        discussion_participants = self._select_discussion_participants(consumer_voice)

        # Build rich participant profiles
        participant_profiles = []
        for i, p in enumerate(discussion_participants, 1):
            rubric = p.get("rubric_scores", {})
            rubric_summary = ", ".join(f"{k}={v}" for k, v in list(rubric.items())[:4]) if rubric else "无评分"
            participant_profiles.append(
                f"参与者{i} [{p.get('persona_name', '未知')}]:\n"
                f"  立场: {p.get('stance', 'unknown')}\n"
                f"  购买意愿: {p.get('purchase_intent', 'unknown')} (得分: {p.get('purchase_score', '?')})\n"
                f"  核心观点: {p.get('voice_line', '')[:200]}\n"
                f"  评分维度: {rubric_summary}\n"
                f"  主要顾虑: {p.get('concerns', '')[:150]}\n"
                f"  关键决策因素: {p.get('decision_logic', '')[:150]}"
            )

        discussion_prompt = f"""你是一个专业的定性研究主持人，正在组织一场消费者焦点小组讨论。

研究问题: {research_input.user_question}
产品信息: {research_input.product_info}

参与者详细资料:
{chr(10).join(participant_profiles)}

请按以下三轮结构模拟讨论:

**第一轮 — 立场陈述**: 每位参与者简要表达对产品的初始看法和购买意愿。

**第二轮 — 交叉反应**: 参与者针对不同观点进行回应，主持人引导深入讨论分歧点。
要求: 每位参与者至少回应一位其他参与者的观点，说明同意或反对的理由。

**第三轮 — 共识探索**: 主持人总结讨论，尝试引导参与者达成共识。
如果无法达成共识，明确记录分歧点和各方坚持的理由。

请返回严格的 JSON 格式:
{{
  "discussion_rounds": [
    {{
      "round": 1,
      "topic": "立场陈述",
      "exchanges": [
        {{"speaker": "参与者名", "statement": "发言内容", "stance_summary": "buy/reject/neutral"}}
      ]
    }},
    {{
      "round": 2,
      "topic": "交叉反应",
      "exchanges": [
        {{"speaker": "参与者名", "statement": "回应内容", "reaction_to": "被回应的参与者名", "agreement_level": "agree/disagree/partial"}}
      ]
    }},
    {{
      "round": 3,
      "topic": "共识探索",
      "exchanges": [
        {{"speaker": "参与者名/主持人", "statement": "总结或最终观点"}}
      ]
    }}
  ],
  "key_conflicts": ["分歧点1", "分歧点2"],
  "emerging_consensus": ["共识1", "共识2"],
  "unresolved_issues": ["未解决问题1"],
  "divergence_score": 0.0-1.0
}}"""

        try:
            result = self.ai_client.generate_text(
                prompt=discussion_prompt,
                system_prompt=(
                    "You are a professional qualitative research moderator conducting a focus group. "
                    "Return valid JSON only. All text must be in Chinese."
                ),
            )

            if result.get("mode") != "live_text":
                logger.warning("Group discussion returned non-live mode: %s", result.get("mode"))
                return {"status": "failed", "reason": "LLM did not return live response"}

            discussion_data = _parse_json_object(result.get("text", ""))

            # Compute divergence score from rubric if not provided by LLM
            divergence_score = discussion_data.get("divergence_score")
            if divergence_score is None:
                divergence_score = self._compute_divergence_score(consumer_voice)

            return {
                "status": "completed",
                "participants": [p.get("persona_name") for p in discussion_participants],
                "discussion_rounds": discussion_data.get("discussion_rounds", []),
                "key_conflicts": discussion_data.get("key_conflicts", []),
                "emerging_consensus": discussion_data.get("emerging_consensus", []),
                "unresolved_issues": discussion_data.get("unresolved_issues", []),
                "divergence_score": divergence_score,
            }
        except Exception as exc:
            logger.warning("Group discussion failed: %s", exc, exc_info=True)
            return {"status": "failed", "reason": str(exc)}

    def _compute_divergence_score(self, consumer_voice: List[Dict[str, Any]]) -> float:
        """Compute inter-persona divergence from purchase_intent distribution."""
        if len(consumer_voice) < 2:
            return 0.0
        intents = [v.get("purchase_intent", "neutral") for v in consumer_voice]
        unique_intents = set(intents)
        if len(unique_intents) <= 1:
            return 0.1
        # Higher diversity = higher divergence
        from collections import Counter
        counts = Counter(intents)
        max_ratio = max(counts.values()) / len(intents)
        return round(1.0 - max_ratio, 2)

    def _select_deep_dive_personas(
        self,
        consumer_voice: List[Dict[str, Any]],
        group_discussion: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Select personas for deep dive based on conflict participation and stance extremes."""
        key_conflicts = group_discussion.get("key_conflicts", [])
        unresolved = group_discussion.get("unresolved_issues", [])
        if not key_conflicts and not unresolved:
            return []

        selected: List[Dict[str, Any]] = []
        # Pick one from each extreme stance
        for target_stance in ["rejecting", "interested", "supportive"]:
            for voice in consumer_voice:
                if voice.get("stance") == target_stance and voice not in selected:
                    selected.append(voice)
                    break

        # Also include personas that appeared in discussion rounds as dissenters
        discussion_rounds = group_discussion.get("discussion_rounds", [])
        dissenters = set()
        for rnd in discussion_rounds:
            for ex in rnd.get("exchanges", []):
                if ex.get("agreement_level") == "disagree":
                    dissenters.add(ex.get("speaker", ""))
        for voice in consumer_voice:
            if voice.get("persona_name") in dissenters and voice not in selected:
                selected.append(voice)

        # Cap at 3 to control LLM cost
        return selected[:3]

    def _run_deep_dive(
        self,
        consumer_voice: List[Dict[str, Any]],
        group_discussion: Dict[str, Any],
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Layer 3: Iterative deep dive with conflict-driven persona selection.

        Each selected persona receives:
          1. Their original position + group discussion highlights
          2. Specific probing questions about unresolved issues
          3. A "what would change your mind" challenge from opposing viewpoints
        """
        if group_discussion.get("status") != "completed":
            return {"status": "skipped", "reason": "Group discussion not completed"}

        deep_dive_personas = self._select_deep_dive_personas(consumer_voice, group_discussion)
        if not deep_dive_personas:
            return {"status": "skipped", "reason": "No suitable personas for deep dive"}

        key_conflicts = group_discussion.get("key_conflicts", [])
        unresolved_issues = group_discussion.get("unresolved_issues", [])
        consensus_points = group_discussion.get("emerging_consensus", [])

        # Build opposing viewpoints summary for cross-challenge
        opposing_views = {}
        for voice in consumer_voice:
            name = voice.get("persona_name", "")
            if name:
                opposing_views[name] = {
                    "stance": voice.get("stance", "unknown"),
                    "voice_line": voice.get("voice_line", "")[:150],
                }

        deep_dive_results = []
        for persona_output in deep_dive_personas:
            persona_name = persona_output.get("persona_name", "未知")

            # Find opposing persona viewpoints for cross-challenge
            other_views = []
            for name, view in opposing_views.items():
                if name != persona_name and view["stance"] != persona_output.get("stance"):
                    other_views.append(f"- {name} ({view['stance']}): \"{view['voice_line']}\"")

            deep_dive_prompt = f"""你正在扮演 {persona_name} 接受深度访谈。

你的原始立场: {persona_output.get('stance', 'unknown')}
你的购买意愿: {persona_output.get('purchase_intent', 'unknown')}
你的核心观点: {persona_output.get('voice_line', '')}
你的主要顾虑: {persona_output.get('concerns', '')[:200]}

在焦点小组讨论中:

**出现的分歧:**
{chr(10).join(f'- {c}' for c in key_conflicts[:3])}

**未解决的问题:**
{chr(10).join(f'- {u}' for u in unresolved_issues[:3])}

**已达成的共识:**
{chr(10).join(f'- {c}' for c in consensus_points[:3]) if consensus_points else '- 暂无'}

**其他参与者的不同观点:**
{chr(10).join(other_views[:3]) if other_views else '- 暂无'}

请从你的消费者视角完成以下深度探索:

1. **立场精细化**: 听完讨论后，你的立场有变化吗？请具体说明哪些因素让你更坚定或动摇。

2. **深层推理**: 跳过表面原因，谈谈让你做出这个判断的真正底层原因（生活经历、价值观、使用习惯等）。

3. **回应反对意见**: 针对与你意见不同的人，具体回应他们的论点。你同意他们的哪些部分？反对哪些部分？为什么？

4. **改变条件**: 请非常具体地描述：什么产品改进、价格调整、信息补充或体验变化会让你改变当前的判断？

返回严格的 JSON 格式:
{{
  "refined_stance": "经过讨论后更明确的立场描述",
  "stance_shifted": true/false,
  "deeper_reasoning": "深层考虑因素",
  "response_to_others": "对不同观点的具体回应",
  "what_would_change_mind": "具体的改变条件",
  "key_barrier_or_driver": "最关键的阻碍或驱动因素"
}}"""

            try:
                result = self.ai_client.generate_text(
                    prompt=deep_dive_prompt,
                    system_prompt=(
                        "You are a consumer persona in a deep-dive interview after a focus group. "
                        "Return valid JSON only. All text must be in Chinese."
                    ),
                )

                if result.get("mode") == "live_text":
                    deep_data = _parse_json_object(result.get("text", ""))
                    deep_dive_results.append({
                        "persona_name": persona_name,
                        "original_stance": persona_output.get("stance"),
                        "original_intent": persona_output.get("purchase_intent"),
                        "refined_stance": deep_data.get("refined_stance", ""),
                        "stance_shifted": deep_data.get("stance_shifted", False),
                        "deeper_reasoning": deep_data.get("deeper_reasoning", ""),
                        "response_to_others": deep_data.get("response_to_others", ""),
                        "what_would_change_mind": deep_data.get("what_would_change_mind", ""),
                        "key_barrier_or_driver": deep_data.get("key_barrier_or_driver", ""),
                    })
            except Exception as exc:
                logger.warning("Deep dive failed for persona %s: %s", persona_name, exc)

        return {
            "status": "completed" if deep_dive_results else "failed",
            "deep_dive_personas": [p.get("persona_name") for p in deep_dive_personas],
            "results": deep_dive_results,
        }

    def _run_personas_concurrent(
        self,
        personas: List[Dict[str, Any]],
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Run all persona agents concurrently with asyncio.gather.

        Per testing-and-operations.md:
        - Execute all eight personas concurrently
        - Target P90 under 45s
        - If >60s, produce partial summary from returned results
        """
        async def _run_single(persona: Dict[str, Any]) -> Dict[str, Any]:
            started_at = time.perf_counter()
            persona_yaml = self.persona_yamls.get(persona["segment_id"], {})
            agent = MomPersonaAgent(persona, self.ai_client, persona_yaml=persona_yaml)
            result = agent.run(research_input, research_plan)
            result["latency_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
            return result

        async def _run_all():
            tasks = [asyncio.create_task(_run_single(p)) for p in personas]
            results: List[Dict[str, Any]] = []
            try:
                completed = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=PERSONA_TIMEOUT_SECONDS,
                )
                errors = [item for item in completed if isinstance(item, Exception)]
                if errors:
                    raise errors[0]
                for item in completed:
                    if isinstance(item, dict):
                        results.append(item)
            except asyncio.TimeoutError:
                # Partial results: gather what we have
                failed_count = 0
                for task in tasks:
                    if task.done() and not task.cancelled():
                        try:
                            result = task.result()
                            if isinstance(result, dict):
                                results.append(result)
                        except Exception as exc:
                            failed_count += 1
                            logger.warning(
                                "Persona task failed during timeout recovery: %s",
                                exc,
                                exc_info=True,
                            )
                if failed_count > 0:
                    logger.warning(
                        "Persona fan-out had %d failed tasks out of %d total",
                        failed_count,
                        len(tasks),
                    )
                if not results:
                    raise IncompleteResearchRunError("Persona fan-out timed out before any result completed.")
            return results

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If already in an event loop, run synchronously as fallback
            return self._run_personas_sync(personas, research_input, research_plan)

        return asyncio.run(_run_all())

    def _run_personas_sync(
        self,
        personas: List[Dict[str, Any]],
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Synchronous fallback for when we're already inside an event loop."""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

        results: List[Dict[str, Any]] = []

        def _run_single_persona(persona: Dict[str, Any]) -> Dict[str, Any]:
            started_at = time.perf_counter()
            persona_yaml = self.persona_yamls.get(persona["segment_id"], {})
            agent = MomPersonaAgent(persona, self.ai_client, persona_yaml=persona_yaml)
            result = agent.run(research_input, research_plan)
            result["latency_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
            return result

        # Use ThreadPoolExecutor to add timeout support for sync execution
        max_workers = min(len(personas), 4)  # Limit concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_persona = {
                executor.submit(_run_single_persona, persona): persona
                for persona in personas
            }
            for future in future_to_persona:
                persona = future_to_persona[future]
                try:
                    result = future.result(timeout=PERSONA_TIMEOUT_SECONDS)
                    results.append(result)
                except FuturesTimeoutError:
                    logger.warning(
                        "Persona %s timed out after %d seconds in sync execution",
                        persona.get("segment_id", "unknown"),
                        PERSONA_TIMEOUT_SECONDS,
                    )
                except Exception as exc:
                    logger.warning(
                        "Persona %s failed in sync execution: %s",
                        persona.get("segment_id", "unknown"),
                        exc,
                        exc_info=True,
                    )

        if not results:
            raise IncompleteResearchRunError("All persona executions failed or timed out in sync mode.")

        return results

    def _ensure_ai_client(self) -> None:
        if self.ai_client is None or not hasattr(self.ai_client, "generate_text"):
            raise IncompleteResearchRunError("AI client is missing.")
        if hasattr(self.ai_client, "is_configured") and not self.ai_client.is_configured:
            raise IncompleteResearchRunError("AI client is not configured.")

    def _load_personas(self) -> List[Dict[str, Any]]:
        payload = json.loads(self.persona_path.read_text(encoding="utf-8"))
        samples = payload.get("samples", [])
        representatives: Dict[str, Dict[str, Any]] = {}
        for sample in samples:
            representatives.setdefault(sample["segment_id"], sample)
        return [representatives[key] for key in sorted(representatives)]

    def _load_persona_yamls(self) -> Dict[str, Dict[str, Any]]:
        """Load persona YAML files from the personas/ directory."""
        personas_dir = self.persona_path.resolve().parent / "personas"
        if not personas_dir.is_dir():
            return {}
        try:
            from backend.domain.persona_scoring import load_all_persona_yamls

            return load_all_persona_yamls(personas_dir)
        except Exception:
            return {}

    def _select_personas_from_plan(self, research_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        selected = []
        for persona_id in research_plan["target_personas"]:
            persona = self._find_persona(persona_id)
            if persona is None:
                raise IncompleteResearchRunError(f"Unknown persona_id in research plan: {persona_id}")
            selected.append(persona)
        return selected

    def _find_persona(self, persona_id: str) -> Dict[str, Any] | None:
        for persona in self.personas:
            if persona_id in {persona["segment_id"], persona.get("sample_id", "")}:
                return persona
        return None
