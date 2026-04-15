"""
CI Blocking Test: Veto Override Structured

Per testing-and-operations.md §test_veto_override_structured.py:
Verify that veto overrides use structured code matching, not free-text
matching, and that the veto properly forces reject intent.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence_models import PersonaEvaluation
from persona_scoring import check_veto, _get_veto_rules


class TestVetoOverrideStructured(unittest.TestCase):
    """Veto overrides must use structured codes, not free-text."""

    def test_structured_veto_code_matches_yaml_rules(self):
        """Structured veto code must match against veto_rules list."""
        persona_yaml = {
            "veto_rules": [
                {"code": "not_imported", "description": "非进口"},
                {"code": "no_authority_endorsement", "description": "无权威背书"},
            ],
            "veto_trigger": "非进口 / 无权威背书",
        }
        persona_output = {
            "triggered_veto_codes": ["not_imported"],
            "verbatim_answer": "这个牙膏挺好的",
            "rubric_scores": {"efficacy_clarity": 4, "trust_signal": 4, "convenience": 4, "price_fit": 4},
        }

        self.assertTrue(check_veto(persona_yaml, "国产儿童牙膏", persona_output))

    def test_unrecognized_veto_code_still_triggers_when_no_allowlist(self):
        """When veto_rules is empty, any triggered code should still trigger veto."""
        persona_yaml = {"veto_trigger": ""}
        persona_output = {
            "triggered_veto_codes": ["custom_concern"],
            "verbatim_answer": "不太放心",
            "rubric_scores": {"efficacy_clarity": 4, "trust_signal": 4, "convenience": 4, "price_fit": 4},
        }

        self.assertTrue(check_veto(persona_yaml, "test product", persona_output))

    def test_veto_forces_reject_intent_regardless_of_high_scores(self):
        """Veto must override purchase_intent to reject even with perfect scores."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=5,
            trust_signal=5,
            convenience=5,
            price_fit=5,
            veto_triggered=True,
        )
        self.assertEqual(evaluation.purchase_intent, "reject")
        self.assertGreater(evaluation.purchase_score, 4.0)

    def test_veto_sets_final_rejection_reason_to_veto_override(self):
        """When veto triggers, final_rejection_reason must be 'veto_override'."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=5,
            trust_signal=5,
            convenience=5,
            price_fit=5,
            veto_triggered=True,
        )
        self.assertEqual(evaluation.final_rejection_reason, "veto_override")

    def test_low_score_reject_sets_final_rejection_reason_to_low_score(self):
        """When rejected due to low scores, final_rejection_reason must be 'low_score'."""
        evaluation = PersonaEvaluation(
            efficacy_clarity=1,
            trust_signal=1,
            convenience=1,
            price_fit=1,
            veto_triggered=False,
        )
        self.assertEqual(evaluation.purchase_intent, "reject")
        self.assertEqual(evaluation.final_rejection_reason, "low_score")

    def test_get_veto_rules_prefers_structured_over_legacy(self):
        """_get_veto_rules must prefer structured veto_rules over legacy veto_trigger."""
        persona_yaml = {
            "veto_rules": [
                {"code": "too_expensive", "description": "太贵"},
            ],
            "veto_trigger": "太贵 / 使用太麻烦 / 安全存疑",
        }
        rules = _get_veto_rules(persona_yaml)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["code"], "too_expensive")

    def test_legacy_veto_trigger_generates_synthetic_codes(self):
        """Legacy veto_trigger without veto_rules should generate synthetic codes."""
        persona_yaml = {"veto_trigger": "太贵 / 使用太麻烦"}
        rules = _get_veto_rules(persona_yaml)
        self.assertEqual(len(rules), 2)
        self.assertTrue(all("legacy_veto_" in r["code"] for r in rules))


if __name__ == "__main__":
    unittest.main()
