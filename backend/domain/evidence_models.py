"""
Evidence data contracts — EvidenceAtom, RASynthesisInternal, PersonaEvaluation.

These Pydantic models enforce the math-decoupling rule:
  • Persona nodes emit discrete 1-5 rubric scores only.
  • Backend code computes weighted totals and purchase_intent.
  • Veto overrides are enforced after scoring.
  • Evaluation dimensions are dynamic per task_type (see scoring_registry).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------- #
#  Evidence Atoms                                                         #
# ---------------------------------------------------------------------- #

class EvidenceAtom(BaseModel):
    """Single piece of structured evidence extracted from a persona output."""

    agent_id: str
    persona_name: str
    field: str = "other"
    value: str
    weight_hint: float = 1.0
    is_minority: bool = False


class RASynthesisInternal(BaseModel):
    """RA must summarize only from extracted evidence atoms."""

    top_consensus_evidence: List[EvidenceAtom] = Field(default_factory=list)
    top_divergence_evidence: List[EvidenceAtom] = Field(default_factory=list)
    minority_reject_evidence: List[EvidenceAtom] = Field(default_factory=list)


# ---------------------------------------------------------------------- #
#  Persona Evaluation — math-decoupled scoring                            #
# ---------------------------------------------------------------------- #

DEFAULT_WEIGHTS: Dict[str, float] = {
    "efficacy_clarity": 0.35,
    "trust_signal": 0.25,
    "convenience": 0.25,
    "price_fit": 0.15,
}


class PersonaEvaluation(BaseModel):
    """Backend-computed evaluation from discrete persona scores.

    Supports both legacy fixed dimensions (efficacy_clarity/trust_signal/
    convenience/price_fit) and dynamic dimensions from scoring_registry.

    Persona nodes emit only integer rubric scores (1-5 each).
    The model_validator computes purchase_score and purchase_intent
    using decision_weights and veto_triggered — never the LLM.
    """

    persona_id: str = ""
    persona_name: str = ""

    # Dynamic rubric scores (1-5) — emitted by persona LLM
    rubric_scores: Dict[str, int] = Field(default_factory=dict)

    # Legacy fixed fields (kept for backward compatibility)
    efficacy_clarity: int = Field(default=3, ge=1, le=5)
    trust_signal: int = Field(default=3, ge=1, le=5)
    convenience: int = Field(default=3, ge=1, le=5)
    price_fit: int = Field(default=3, ge=1, le=5)

    # Veto flag — set by backend after checking persona YAML veto_trigger
    veto_triggered: bool = False

    # Backend-only decision weights (loaded from persona YAML or scoring_registry)
    decision_weights: Dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    # Scoring thresholds (from scoring_registry per task_type)
    buy_threshold: float = 4.0
    reject_threshold: float = 2.8

    # Computed fields (set by validator, never by LLM)
    purchase_score: Optional[float] = None
    purchase_intent: Optional[Literal["buy", "maybe", "reject"]] = None
    final_rejection_reason: str = ""
    winner_signal: Optional[float] = None  # A/B test only: positive=A wins, negative=B wins

    @model_validator(mode="after")
    def compute_intent(self) -> "PersonaEvaluation":
        w = self.decision_weights or DEFAULT_WEIGHTS

        # Use rubric_scores if populated, otherwise fall back to legacy fields
        scores = self.rubric_scores
        if not scores:
            scores = {
                "efficacy_clarity": self.efficacy_clarity,
                "trust_signal": self.trust_signal,
                "convenience": self.convenience,
                "price_fit": self.price_fit,
            }

        # A/B test directionality: compute winner_signal from option scores
        if "option_a_alignment" in scores and "option_b_alignment" in scores:
            self.winner_signal = round(
                scores["option_a_alignment"] - scores["option_b_alignment"], 4
            )

        # Compute weighted sum over all dimensions present in weights
        total_weight = sum(w.get(dim, 0.0) for dim in scores)
        if total_weight > 0:
            score = sum(
                scores.get(dim, 3) * w.get(dim, 0.0) for dim in scores
            ) / total_weight
        else:
            score = sum(scores.values()) / len(scores) if scores else 3.0

        self.purchase_score = round(score, 4)

        if self.veto_triggered:
            self.purchase_intent = "reject"
            self.final_rejection_reason = "veto_override"
        elif score < self.reject_threshold:
            self.purchase_intent = "reject"
            self.final_rejection_reason = "low_score"
        elif score >= self.buy_threshold:
            self.purchase_intent = "buy"
            self.final_rejection_reason = ""
        else:
            self.purchase_intent = "maybe"
            self.final_rejection_reason = ""
        return self
