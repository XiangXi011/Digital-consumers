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

    def test_below_2_8_threshold_is_reject(self):
        """Score below 2.8 must be 'reject'."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=2,
            trust_signal=4,
            convenience=2,
            price_fit=2,
            decision_weights={
                "efficacy_clarity": 0.40,
                "trust_signal": 0.20,
                "convenience": 0.20,
                "price_fit": 0.20,
            },
        )
        # 2*0.40 + 4*0.20 + 2*0.20 + 2*0.20 = 0.80 + 0.80 + 0.40 + 0.40 = 2.40 -> reject
        self.assertLess(evaluation.purchase_score, 2.8)
        self.assertEqual(evaluation.purchase_intent, "reject")

    def test_exact_boundary_at_2_8_is_maybe(self):
        """Score exactly at or above 2.8 threshold must be 'maybe'."""
        # Use weights to produce a score exactly at 2.8
        # 3*0.50 + 2*0.50 = 1.50 + 1.00 = 2.50 (reject)
        # 3*0.50 + 3*0.50 = 1.50 + 1.50 = 3.00 (maybe)
        # Try to land at exactly 2.8:
        evaluation = PersonaEvaluation(
            rubric_scores={"dim_a": 3, "dim_b": 2},
            decision_weights={
                "dim_a": 0.60,
                "dim_b": 0.40,
            },
        )
        # 3*0.60 + 2*0.40 = 1.80 + 0.80 = 2.60 -> reject (below 2.8)
        self.assertLess(evaluation.purchase_score, 2.8)

        evaluation2 = PersonaEvaluation(
            rubric_scores={"dim_a": 3, "dim_b": 3},
            decision_weights={
                "dim_a": 0.50,
                "dim_b": 0.50,
            },
        )
        # 3*0.50 + 3*0.50 = 3.00 -> maybe
        self.assertGreaterEqual(evaluation2.purchase_score, 2.8)
        self.assertLess(evaluation2.purchase_score, 4.0)
        self.assertEqual(evaluation2.purchase_intent, "maybe")

        # Now test exactly at 2.8 boundary
        evaluation_boundary = PersonaEvaluation(
            efficacy_clarity=4,
            trust_signal=2,
            convenience=2,
            price_fit=2,
            decision_weights={
                "efficacy_clarity": 0.40,
                "trust_signal": 0.20,
                "convenience": 0.20,
                "price_fit": 0.20,
            },
        )
        # 4*0.40 + 2*0.20 + 2*0.20 + 2*0.20 = 1.60 + 0.40 + 0.40 + 0.40 = 2.80 -> maybe (>= 2.8)
        self.assertAlmostEqual(evaluation_boundary.purchase_score, 2.8, places=4)
        self.assertEqual(evaluation_boundary.purchase_intent, "maybe")

    def test_exact_boundary_at_4_0_threshold(self):
        """Score exactly at 4.0 must be 'buy', not 'maybe'."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=4,
            trust_signal=4,
            convenience=4,
            price_fit=4,
        )
        self.assertAlmostEqual(evaluation.purchase_score, 4.0, places=4)
        self.assertEqual(evaluation.purchase_intent, "buy")

        # Just below 4.0
        evaluation_below = PersonaEvaluation(
            efficacy_clarity=4,
            trust_signal=4,
            convenience=4,
            price_fit=3,
            decision_weights={
                "efficacy_clarity": 0.35,
                "trust_signal": 0.25,
                "convenience": 0.25,
                "price_fit": 0.15,
            },
        )
        # 4*0.35 + 4*0.25 + 4*0.25 + 3*0.15 = 1.40 + 1.00 + 1.00 + 0.45 = 3.85 -> maybe
        self.assertAlmostEqual(evaluation_below.purchase_score, 3.85, places=4)
        self.assertEqual(evaluation_below.purchase_intent, "maybe")

    def test_final_rejection_reason_set_correctly(self):
        """final_rejection_reason must be set for reject, empty for non-reject."""
        veto_eval = PersonaEvaluation(
            efficacy_clarity=5, trust_signal=5, convenience=5, price_fit=5,
            veto_triggered=True,
        )
        self.assertEqual(veto_eval.final_rejection_reason, "veto_override")

        low_eval = PersonaEvaluation(
            efficacy_clarity=1, trust_signal=1, convenience=1, price_fit=1,
        )
        self.assertEqual(low_eval.final_rejection_reason, "low_score")

        buy_eval = PersonaEvaluation(
            efficacy_clarity=5, trust_signal=5, convenience=5, price_fit=5,
        )
        self.assertEqual(buy_eval.final_rejection_reason, "")

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

    def test_structured_veto_codes_override_without_keyword_matching(self):
        """Structured veto codes should be honored even if text does not contain trigger keywords."""
        from persona_scoring import check_veto

        persona_yaml = {
            "veto_rules": [
                {"code": "unsafe_signal", "description": "Safety concern"},
            ],
            "veto_trigger": "安全存疑 / 使用太麻烦",
        }
        persona_output = {
            "verbatim_answer": "我会再看看",
            "triggered_veto_codes": ["unsafe_signal"],
            "rubric_scores": {
                "efficacy_clarity": 4,
                "trust_signal": 4,
                "convenience": 4,
                "price_fit": 4,
            },
        }

        self.assertTrue(check_veto(persona_yaml, "儿童牙膏", persona_output))


if __name__ == "__main__":
    unittest.main()
