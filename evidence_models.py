"""
Evidence data contracts — EvidenceAtom, RASynthesisInternal, PersonaEvaluation.

These Pydantic models enforce the math-decoupling rule:
  • Persona nodes emit discrete 1-5 rubric scores only.
  • Backend code computes weighted totals and purchase_intent.
  • Veto overrides are enforced after scoring.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------- #
#  Evidence Atoms                                                         #
# ---------------------------------------------------------------------- #

class EvidenceAtom(BaseModel):
    """Single piece of structured evidence extracted from a persona output."""

    agent_id: str
    persona_name: str
    field: Literal["efficacy", "trust", "price", "convenience", "other"]
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

    Persona nodes emit only the four integer fields (1-5 each).
    The model_validator computes purchase_score and purchase_intent
    using decision_weights and veto_triggered — never the LLM.
    """

    persona_id: str = ""
    persona_name: str = ""

    # Discrete rubric scores (1-5) — emitted by persona LLM
    efficacy_clarity: int = Field(ge=1, le=5)
    trust_signal: int = Field(ge=1, le=5)
    convenience: int = Field(ge=1, le=5)
    price_fit: int = Field(ge=1, le=5)

    # Veto flag — set by backend after checking persona YAML veto_trigger
    veto_triggered: bool = False

    # Backend-only decision weights (loaded from persona YAML)
    decision_weights: Dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    # Computed fields (set by validator, never by LLM)
    purchase_score: Optional[float] = None
    purchase_intent: Optional[Literal["buy", "maybe", "reject"]] = None

    @model_validator(mode="after")
    def compute_intent(self) -> "PersonaEvaluation":
        w = self.decision_weights or DEFAULT_WEIGHTS
        score = (
            self.efficacy_clarity * w.get("efficacy_clarity", 0.35)
            + self.trust_signal * w.get("trust_signal", 0.25)
            + self.convenience * w.get("convenience", 0.25)
            + self.price_fit * w.get("price_fit", 0.15)
        )
        self.purchase_score = round(score, 4)
        if self.veto_triggered:
            self.purchase_intent = "reject"
        elif score < 2.8:
            self.purchase_intent = "reject"
        elif score >= 4.0:
            self.purchase_intent = "buy"
        else:
            self.purchase_intent = "maybe"
        return self
