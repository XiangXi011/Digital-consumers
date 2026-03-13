"""
BusinessBrief — the only downstream business context.

All planner, persona, and RA nodes must consume this typed contract
instead of raw chat text or untyped dicts.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class BusinessBrief(BaseModel):
    """Canonical business context per data-contracts.md."""

    task_type: Literal[
        "concept_test", "copy_feedback", "ab_test", "price_test", "unknown"
    ] = "unknown"
    product_context: str = ""
    research_goal: str = ""

    # Target & channel metadata
    target_age: Optional[str] = None
    channel: Optional[str] = None
    brand: Optional[str] = None

    # Price-test specifics
    price_test_mode: Optional[
        Literal["absolute_price", "relative_price", "promo_vs_daily"]
    ] = None
    price_range: Optional[str] = None
    benchmark_reference: Optional[List[str]] = None
    pack_size_or_volume: Optional[str] = None
    price_anchor_type: Optional[
        Literal["competitor", "category_norm", "historical_price", "promo_anchor"]
    ] = None

    # Assets & claims
    copy_candidates: Optional[List[str]] = None
    concept_assets: Optional[List[str]] = None
    key_claims: List[str] = Field(default_factory=list)

    # Assumptions & risk
    assumptions: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    source_evidence_spans: List[str] = Field(default_factory=list)

    # Follow-up linkage
    followup_relation: Optional[
        Literal["same_task", "same_topic_new_task", "unrelated"]
    ] = None
    prior_brief_snapshot_ref: Optional[str] = None

    @model_validator(mode="after")
    def validate_price_constraints(self):
        if self.task_type == "price_test":
            if not self.price_test_mode:
                raise ValueError("price_test requires price_test_mode")
            if not self.price_range:
                raise ValueError("price_test requires price_range")
            if self.price_test_mode == "relative_price" and not self.benchmark_reference:
                raise ValueError("relative_price requires benchmark_reference")
            if self.price_test_mode == "promo_vs_daily":
                if self.price_anchor_type not in {"historical_price", "promo_anchor"}:
                    raise ValueError("promo_vs_daily requires valid price_anchor_type")
        return self

    # ------------------------------------------------------------------ #
    #  Factory helpers                                                     #
    # ------------------------------------------------------------------ #

    _QUESTION_TYPE_TO_TASK_TYPE: ClassVar[Dict[str, str]] = {
        "product_concept": "concept_test",
        "copy_feedback": "copy_feedback",
        "purchase_decision": "concept_test",
        "needs_pain_points": "concept_test",
    }

    @classmethod
    def from_session_fields(cls, fields: Dict[str, Dict[str, Any]], **extra: Any) -> "BusinessBrief":
        """Build a BusinessBrief from a TaskSession.fields dict.

        This bridges the existing session-collection flow into the typed
        contract so downstream nodes never touch raw chat.
        """
        def _val(key: str) -> str:
            entry = fields.get(key, {})
            value = entry.get("value")
            return "" if value is None else str(value)

        question_type = _val("question_type")
        task_type = cls._QUESTION_TYPE_TO_TASK_TYPE.get(question_type, "unknown")

        user_question = _val("user_question")
        product_info = _val("product_info")
        copy_material = _val("copy_material")
        background_material = _val("background_material")

        key_claims: List[str] = []
        if copy_material:
            key_claims = [c.strip() for c in copy_material.split("，") if c.strip()]
            if len(key_claims) <= 1:
                key_claims = [c.strip() for c in copy_material.split(",") if c.strip()]
            if len(key_claims) <= 1:
                key_claims = [copy_material]

        return cls(
            task_type=task_type,
            product_context=product_info or background_material,
            research_goal=user_question,
            key_claims=key_claims,
            brand=extra.get("brand"),
            channel=extra.get("channel"),
            target_age=extra.get("target_age"),
            **{k: v for k, v in extra.items() if k in cls.model_fields and k not in ("brand", "channel", "target_age")},
        )
