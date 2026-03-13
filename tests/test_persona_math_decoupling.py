"""
CI Blocking Test: Persona Math Decoupling

Per testing-and-operations.md §test_persona_math_decoupling.py:
Feed persona output with only base feature scores and verify backend code
computes the final score and purchase intent. If all rubric scores are low,
backend must force reject behavior.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence_models import PersonaEvaluation


class TestPersonaMathDecoupling(unittest.TestCase):
    """Backend must compute weighted totals — persona LLM must not."""

    def test_backend_computes_weighted_score(self):
        """Given base feature scores, backend must compute purchase_score."""
        evaluation = PersonaEvaluation(
            persona_id="M04",
            persona_name="高线忙碌派",
            efficacy_clarity=4,
            trust_signal=4,
            convenience=4,
            price_fit=4,
            decision_weights={
                "efficacy_clarity": 0.35,
                "trust_signal": 0.25,
                "convenience": 0.25,
                "price_fit": 0.15,
            },
        )
        self.assertIsNotNone(evaluation.purchase_score)
        self.assertAlmostEqual(evaluation.purchase_score, 4.0, places=2)
        self.assertEqual(evaluation.purchase_intent, "buy")

    def test_backend_computes_maybe_for_moderate_scores(self):
        """Moderate scores (3) should produce 'maybe' intent."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=3,
            trust_signal=3,
            convenience=3,
            price_fit=3,
        )
        self.assertAlmostEqual(evaluation.purchase_score, 3.0, places=2)
        self.assertEqual(evaluation.purchase_intent, "maybe")

    def test_low_scores_force_reject_intent(self):
        """All low scores (2) produce reject (score 2.0 < 2.8 threshold)."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=2,
            trust_signal=2,
            convenience=2,
            price_fit=2,
        )
        self.assertAlmostEqual(evaluation.purchase_score, 2.0, places=2)
        self.assertEqual(evaluation.purchase_intent, "reject")

    def test_veto_overrides_high_scores_to_reject(self):
        """Even with high scores, veto must force reject."""
        evaluation = PersonaEvaluation(
            persona_id="M01",
            persona_name="宠爱富养家",
            efficacy_clarity=5,
            trust_signal=5,
            convenience=5,
            price_fit=5,
            veto_triggered=True,
        )
        self.assertEqual(evaluation.purchase_intent, "reject")
        # purchase_score is computed but intent is overridden
        self.assertIsNotNone(evaluation.purchase_score)
        self.assertGreater(evaluation.purchase_score, 4.0)

    def test_custom_weights_affect_score(self):
        """Different decision_weights from persona YAML must affect the final score."""
        # M01 weights: trust_signal=0.40, price_fit=0.30
        evaluation = PersonaEvaluation(
            efficacy_clarity=2,
            trust_signal=5,
            convenience=2,
            price_fit=5,
            decision_weights={
                "efficacy_clarity": 0.20,
                "trust_signal": 0.40,
                "convenience": 0.10,
                "price_fit": 0.30,
            },
        )
        expected = 2 * 0.20 + 5 * 0.40 + 2 * 0.10 + 5 * 0.30
        self.assertAlmostEqual(evaluation.purchase_score, expected, places=2)

    def test_minimum_scores_produce_low_intent(self):
        """All minimum scores (1) should produce reject (score 1.0 < 2.8 threshold)."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=1,
            trust_signal=1,
            convenience=1,
            price_fit=1,
        )
        self.assertAlmostEqual(evaluation.purchase_score, 1.0, places=2)
        self.assertEqual(evaluation.purchase_intent, "reject")

    def test_score_range_validation(self):
        """Scores outside 1-5 must be rejected by Pydantic validation."""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            PersonaEvaluation(
                efficacy_clarity=0,  # Below minimum
                trust_signal=3,
                convenience=3,
                price_fit=3,
            )

        with self.assertRaises(ValidationError):
            PersonaEvaluation(
                efficacy_clarity=6,  # Above maximum
                trust_signal=3,
                convenience=3,
                price_fit=3,
            )

    def test_persona_output_must_not_contain_weighted_fields(self):
        """Validate that the mom payload validator rejects weighted fields."""
        from qualitative_research import IncompleteResearchRunError, _validate_mom_payload

        payload = {
            "persona_id": "M04",
            "persona_name": "高线忙碌派-mom",
            "task_responses": [{"question": "test", "answer": "test"}],
            "dimension_scores": [{"dimension": "信任", "judgement": "需要更强证据"}],
            "efficacy_clarity": 4,
            "trust_signal": 4,
            "convenience": 4,
            "price_fit": 4,
            "stance": "interested",
            "core_needs": ["安全"],
            "motivations": ["专业背书"],
            "concerns": ["价格"],
            "decision_logic": "先看证据",
            "verbatim_answer": "会考虑",
            "evidence_trace": "信任驱动",
            "purchase_score": 4.2,  # FORBIDDEN — must be computed by backend
        }

        with self.assertRaises(IncompleteResearchRunError) as context:
            _validate_mom_payload(payload, "M04", "purchase_decision")

        self.assertIn("purchase_score", str(context.exception))


if __name__ == "__main__":
    unittest.main()
