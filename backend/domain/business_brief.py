"""
BusinessBrief: the only downstream business context.

All planner, persona, and RA nodes must consume this typed contract
instead of raw chat text or untyped dicts.
"""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


DEFAULT_EIGHT_MOM_PERSONA_PACK_ID = "default-eight-moms-v1"
DEFAULT_EIGHT_MOM_SEGMENTS = [
    "M01 宠爱富养家",
    "M02 自在成长家",
    "M03 传统关爱妈",
    "M04 高线忙碌派",
    "M05 品质精算师",
    "M06 小镇贵妇妈",
    "M07 全能优等家",
    "M08 佛系粗养家",
]
DEFAULT_EIGHT_MOM_PATTERN = re.compile(r"(?:8|八)\s*类妈妈")
# Negative context: user explicitly rejects the 8-mom pack
NEGATE_EIGHT_MOM_PATTERN = re.compile(r"(?:不|别|别用|不要|不想|无需|不用).*?(?:8|八)\s*类妈妈")


def _text_value(fields: Dict[str, Dict[str, Any]], key: str) -> str:
    entry = fields.get(key, {})
    value = entry.get("value")
    return "" if value is None else str(value).strip()


def _split_items(raw_value: str) -> List[str]:
    if not raw_value.strip():
        return []
    parts = re.split(r"[\n,，；;]+", raw_value)
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned or [raw_value.strip()]


def _uses_default_eight_mom_pack(fields: Dict[str, Dict[str, Any]]) -> bool:
    if _text_value(fields, "mode") == "single":
        return False
    if _text_value(fields, "persona_id"):
        return False

    text_fragments = (
        _text_value(fields, "user_question"),
        _text_value(fields, "product_info"),
        _text_value(fields, "background_material"),
        _text_value(fields, "copy_material"),
    )
    for fragment in text_fragments:
        if fragment and DEFAULT_EIGHT_MOM_PATTERN.search(fragment):
            # Check if user is explicitly rejecting the 8-mom pack
            if NEGATE_EIGHT_MOM_PATTERN.search(fragment):
                continue
            return True
    return False


class BusinessBrief(BaseModel):
    """Canonical business context per data-contracts.md."""

    task_type: Literal[
        "concept_test", "packaging_review", "copy_feedback", "ab_test", "price_test", "unknown"
    ] = "unknown"
    question_type: Optional[str] = None
    product_context: str = ""
    research_goal: str = ""

    target_age: Optional[str] = None
    channel: Optional[str] = None
    brand: Optional[str] = None

    price_test_mode: Optional[
        Literal["absolute_price", "relative_price", "promo_vs_daily"]
    ] = None
    price_range: Optional[str] = None
    benchmark_reference: Optional[List[str]] = None
    pack_size_or_volume: Optional[str] = None
    price_anchor_type: Optional[
        Literal["competitor", "category_norm", "historical_price", "promo_anchor"]
    ] = None

    copy_candidates: Optional[List[str]] = None
    concept_assets: Optional[List[str]] = None
    key_claims: List[str] = Field(default_factory=list)
    source_links: List[str] = Field(default_factory=list)
    custom_questions: List[str] = Field(default_factory=list)
    persona_pack_id: Optional[str] = None
    audience_segments: Optional[List[str]] = None

    assumptions: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    source_evidence_spans: List[str] = Field(default_factory=list)

    followup_relation: Optional[
        Literal["same_task", "same_topic_new_task", "unrelated"]
    ] = None
    prior_brief_snapshot_ref: Optional[str] = None

    _QUESTION_TYPE_TO_TASK_TYPE: ClassVar[Dict[str, str]] = {
        "product_concept": "concept_test",
        "concept_test": "concept_test",
        "packaging_review": "packaging_review",
        "copy_feedback": "copy_feedback",
        "ab_test": "ab_test",
        "purchase_decision": "concept_test",
        "needs_pain_points": "concept_test",
        "price_test": "price_test",
    }
    _TASK_TYPE_TO_QUESTION_TYPE: ClassVar[Dict[str, str]] = {
        "concept_test": "concept_test",
        "packaging_review": "packaging_review",
        "copy_feedback": "copy_feedback",
        "ab_test": "ab_test",
        "price_test": "price_test",
        "unknown": "copy_feedback",
    }

    @classmethod
    def from_session_fields(cls, fields: Dict[str, Dict[str, Any]], **extra: Any) -> "BusinessBrief":
        question_type = _text_value(fields, "question_type")
        task_type = cls._QUESTION_TYPE_TO_TASK_TYPE.get(question_type, "unknown")

        user_question = _text_value(fields, "user_question")
        product_info = _text_value(fields, "product_info")
        background_material = _text_value(fields, "background_material")
        copy_material = _text_value(fields, "copy_material")

        copy_candidates = _split_items(copy_material)
        key_claims = list(copy_candidates)
        source_links = list(extra.get("source_links") or [])
        custom_questions = list(extra.get("custom_questions") or [])
        product_context_notes = [
            str(note).strip()
            for note in (extra.get("product_context_notes") or [])
            if str(note).strip()
        ]

        benchmark_reference = _split_items(_text_value(fields, "benchmark_reference")) or None
        use_default_eight_mom_pack = _uses_default_eight_mom_pack(fields)
        product_context_parts: List[str] = []
        if product_info:
            product_context_parts.append(product_info)
        if background_material:
            product_context_parts.append(background_material)
        for note in product_context_notes:
            if note not in product_context_parts:
                product_context_parts.append(note)
        if source_links:
            product_context_parts.append(f"source_links: {', '.join(source_links)}")

        payload: Dict[str, Any] = {
            "task_type": task_type,
            "question_type": question_type or None,
            "product_context": "\n".join(product_context_parts),
            "research_goal": user_question,
            "copy_candidates": copy_candidates or None,
            "key_claims": key_claims,
            "source_links": source_links,
            "custom_questions": custom_questions,
            "target_age": _text_value(fields, "target_age") or extra.get("target_age"),
            "channel": _text_value(fields, "channel") or extra.get("channel"),
            "brand": _text_value(fields, "brand") or extra.get("brand"),
            "price_test_mode": _text_value(fields, "price_test_mode") or extra.get("price_test_mode"),
            "price_range": _text_value(fields, "price_range") or extra.get("price_range"),
            "benchmark_reference": benchmark_reference or extra.get("benchmark_reference"),
            "pack_size_or_volume": _text_value(fields, "pack_size_or_volume") or extra.get("pack_size_or_volume"),
            "price_anchor_type": _text_value(fields, "price_anchor_type") or extra.get("price_anchor_type"),
            "persona_pack_id": (
                DEFAULT_EIGHT_MOM_PERSONA_PACK_ID
                if use_default_eight_mom_pack
                else extra.get("persona_pack_id")
            ),
            "audience_segments": (
                list(DEFAULT_EIGHT_MOM_SEGMENTS)
                if use_default_eight_mom_pack
                else extra.get("audience_segments")
            ),
            "followup_relation": extra.get("followup_relation"),
            "prior_brief_snapshot_ref": extra.get("prior_brief_snapshot_ref"),
        }

        if task_type not in {"copy_feedback", "ab_test"}:
            payload["copy_candidates"] = None
        if task_type == "ab_test" and not payload["copy_candidates"]:
            payload["copy_candidates"] = None
        if task_type != "price_test":
            payload["price_test_mode"] = None
            payload["price_range"] = None
            payload["benchmark_reference"] = None
            payload["pack_size_or_volume"] = None
            payload["price_anchor_type"] = None

        allowed_extras = {
            key: value
            for key, value in extra.items()
            if key in cls.model_fields and key not in payload
        }
        payload.update(allowed_extras)
        return cls(**payload)

    def to_research_input_payload(
        self,
        *,
        mode: str = "",
        persona_id: str = "",
        attachments: Optional[List[str]] = None,
        follow_up_context: str = "",
        background_material: str = "",
    ) -> Dict[str, Any]:
        copy_material = ""
        if self.copy_candidates:
            copy_material = "\n".join(self.copy_candidates)
        elif self.key_claims:
            copy_material = "\n".join(self.key_claims)

        background_lines = [background_material.strip()] if background_material.strip() else []
        metadata_lines = []
        if self.brand:
            metadata_lines.append(f"brand: {self.brand}")
        if self.channel:
            metadata_lines.append(f"channel: {self.channel}")
        if self.target_age:
            metadata_lines.append(f"target_age: {self.target_age}")
        if self.pack_size_or_volume:
            metadata_lines.append(f"pack_size_or_volume: {self.pack_size_or_volume}")
        if self.price_test_mode:
            metadata_lines.append(f"price_test_mode: {self.price_test_mode}")
        if self.price_range:
            metadata_lines.append(f"price_range: {self.price_range}")
        if self.price_anchor_type:
            metadata_lines.append(f"price_anchor_type: {self.price_anchor_type}")
        if self.benchmark_reference:
            metadata_lines.append(
                f"benchmark_reference: {', '.join(self.benchmark_reference)}"
            )
        if self.persona_pack_id:
            metadata_lines.append(f"persona_pack_id: {self.persona_pack_id}")
        if self.audience_segments:
            metadata_lines.append(
                f"audience_segments: {', '.join(self.audience_segments)}"
            )
        if metadata_lines:
            background_lines.extend(metadata_lines)

        structured_follow_up = ""
        if self.followup_relation and self.followup_relation != "unrelated":
            structured_follow_up = json.dumps(
                {
                    "relation": self.followup_relation,
                    "prior_brief_snapshot_ref": self.prior_brief_snapshot_ref or "",
                },
                ensure_ascii=False,
            )

        return {
            "mode": mode,
            "question_type": self.question_type
            or self._TASK_TYPE_TO_QUESTION_TYPE.get(self.task_type, "copy_feedback"),
            "persona_id": persona_id,
            "user_question": self.research_goal,
            "background_material": "\n".join(line for line in background_lines if line.strip()),
            "product_info": self.product_context,
            "copy_material": copy_material,
            "attachments": list(attachments or []),
            "follow_up_context": structured_follow_up,
            "persona_pack_id": self.persona_pack_id or "",
            "audience_segments": list(self.audience_segments or []),
        }
