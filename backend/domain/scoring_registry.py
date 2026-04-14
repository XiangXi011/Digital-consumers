"""
Scoring dimension registry — maps task_type to evaluation dimensions, weights, and thresholds.

Each review type uses a different set of rubric dimensions so that
the scoring reflects the specific evaluation criteria of that review.
"""

from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------- #
#  Per-task-type dimension configs                                        #
# ---------------------------------------------------------------------- #

TASK_TYPE_SCORING: Dict[str, Dict[str, Any]] = {
    "product_concept": {
        "dimensions": ["demand_fit", "differentiation", "purchase_drive", "price_acceptance"],
        "dimension_labels": {
            "demand_fit": "需求匹配度",
            "differentiation": "差异化认知",
            "purchase_drive": "购买驱动力",
            "price_acceptance": "价格接受度",
        },
        "weights": {
            "demand_fit": 0.35,
            "differentiation": 0.25,
            "purchase_drive": 0.25,
            "price_acceptance": 0.15,
        },
        "persona_weight_mapping": {
            "demand_fit": "efficacy_clarity",
            "differentiation": "trust_signal",
            "purchase_drive": "convenience",
            "price_acceptance": "price_fit",
        },
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    },
    "concept_test": {
        "dimensions": ["demand_fit", "differentiation", "purchase_drive", "price_acceptance"],
        "dimension_labels": {
            "demand_fit": "需求匹配度",
            "differentiation": "差异化认知",
            "purchase_drive": "购买驱动力",
            "price_acceptance": "价格接受度",
        },
        "weights": {
            "demand_fit": 0.35,
            "differentiation": 0.25,
            "purchase_drive": 0.25,
            "price_acceptance": 0.15,
        },
        "persona_weight_mapping": {
            "demand_fit": "efficacy_clarity",
            "differentiation": "trust_signal",
            "purchase_drive": "convenience",
            "price_acceptance": "price_fit",
        },
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    },
    "packaging_review": {
        "dimensions": ["shelf_recognition", "info_clarity", "visual_trust", "pickup_willingness"],
        "dimension_labels": {
            "shelf_recognition": "货架辨识度",
            "info_clarity": "信息清晰度",
            "visual_trust": "视觉信任感",
            "pickup_willingness": "拿起意愿",
        },
        "weights": {
            "shelf_recognition": 0.30,
            "info_clarity": 0.25,
            "visual_trust": 0.25,
            "pickup_willingness": 0.20,
        },
        "persona_weight_mapping": {
            "shelf_recognition": "efficacy_clarity",
            "info_clarity": "trust_signal",
            "visual_trust": "convenience",
            "pickup_willingness": "price_fit",
        },
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    },
    "copy_feedback": {
        "dimensions": ["memory_strength", "credibility", "conversion_power", "emotional_resonance"],
        "dimension_labels": {
            "memory_strength": "记忆点强度",
            "credibility": "可信度",
            "conversion_power": "转化说服力",
            "emotional_resonance": "情感共鸣",
        },
        "weights": {
            "memory_strength": 0.30,
            "credibility": 0.25,
            "conversion_power": 0.25,
            "emotional_resonance": 0.20,
        },
        "persona_weight_mapping": {
            "memory_strength": "efficacy_clarity",
            "credibility": "trust_signal",
            "conversion_power": "convenience",
            "emotional_resonance": "price_fit",
        },
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    },
    "ab_test": {
        "dimensions": ["option_a_alignment", "option_b_alignment", "overall_preference", "switching_cost"],
        "dimension_labels": {
            "option_a_alignment": "方案A维度对齐",
            "option_b_alignment": "方案B维度对齐",
            "overall_preference": "综合偏好",
            "switching_cost": "切换成本",
        },
        "weights": {
            "option_a_alignment": 0.25,
            "option_b_alignment": 0.25,
            "overall_preference": 0.30,
            "switching_cost": 0.20,
        },
        "persona_weight_mapping": {
            "option_a_alignment": "efficacy_clarity",
            "option_b_alignment": "trust_signal",
            "overall_preference": "convenience",
            "switching_cost": "price_fit",
        },
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    },
    "price_test": {
        "dimensions": ["price_sensitivity", "value_perception", "competitive_position", "purchase_willingness"],
        "dimension_labels": {
            "price_sensitivity": "价格敏感度",
            "value_perception": "价值感知",
            "competitive_position": "竞品定位",
            "purchase_willingness": "购买意愿",
        },
        "weights": {
            "price_sensitivity": 0.25,
            "value_perception": 0.30,
            "competitive_position": 0.20,
            "purchase_willingness": 0.25,
        },
        "persona_weight_mapping": {
            "price_sensitivity": "price_fit",
            "value_perception": "efficacy_clarity",
            "competitive_position": "trust_signal",
            "purchase_willingness": "convenience",
        },
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    },
}

# Legacy fallback — maps to original 4 hardcoded dimensions
LEGACY_DIMENSIONS = ["efficacy_clarity", "trust_signal", "convenience", "price_fit"]
LEGACY_WEIGHTS = {
    "efficacy_clarity": 0.35,
    "trust_signal": 0.25,
    "convenience": 0.25,
    "price_fit": 0.15,
}


def get_scoring_config(task_type: str) -> Dict[str, Any]:
    """Get the scoring configuration for a given task type.

    Falls back to legacy dimensions if task_type is unknown.
    """
    config = TASK_TYPE_SCORING.get(task_type)
    if config:
        return config
    return {
        "dimensions": list(LEGACY_DIMENSIONS),
        "dimension_labels": {d: d for d in LEGACY_DIMENSIONS},
        "weights": dict(LEGACY_WEIGHTS),
        "buy_threshold": 4.0,
        "reject_threshold": 2.8,
    }


def get_dimensions(task_type: str) -> List[str]:
    """Get the list of evaluation dimension keys for a task type."""
    return get_scoring_config(task_type)["dimensions"]


def get_weights(task_type: str) -> Dict[str, float]:
    """Get the decision weights for a task type."""
    return get_scoring_config(task_type)["weights"]


def get_dimension_labels(task_type: str) -> Dict[str, str]:
    """Get human-readable labels for each dimension."""
    return get_scoring_config(task_type)["dimension_labels"]
