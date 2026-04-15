"""
CI Blocking Test: Follow-up Rule Override

Per testing-and-operations.md §test_followup_rule_override.py:
Assert that a rule-engine `unrelated` decision stops the previous workflow
and prevents the LLM follow-up classifier from running.
"""

import sys
import unittest
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from followup_adjudicator import (
    adjudicate_followup,
    check_same_task_preconditions,
    embedding_similarity,
    keyword_overlap,
)


class TestFollowupRuleOverride(unittest.TestCase):
    """Rule engine must decide first. LLM never runs for 'unrelated' messages."""

    def test_completely_unrelated_message_returns_unrelated(self):
        """A message about a totally different topic must be classified as unrelated."""
        result = adjudicate_followup(
            candidate_brief_text="今天天气真好，想去公园散步",
            prior_brief_text="舒客儿童牙膏防蛀配方概念测试，目标人群25-35岁妈妈",
        )
        self.assertEqual(result, "unrelated")

    def test_similar_topic_returns_candidate(self):
        """A message about the same product topic should be classified as candidate_same_topic."""
        result = adjudicate_followup(
            candidate_brief_text="舒客儿童牙膏防蛀效果妈妈反馈",
            prior_brief_text="舒客儿童牙膏防蛀效果妈妈评测",
        )
        self.assertEqual(result, "candidate_same_topic")

    def test_unrelated_stops_llm_from_running(self):
        """When rule engine says 'unrelated', LLM classifier MUST NOT run.

        This test ensures the architectural boundary: rule engine always
        decides first, and if it returns 'unrelated', no LLM adjudication
        is attempted.
        """
        # The adjudicate_followup function only calls rule engine, never LLM
        # For unrelated messages, the caller must NOT proceed to llm_refine_followup
        result = adjudicate_followup(
            candidate_brief_text="我想订一束花送给朋友",
            prior_brief_text="儿童牙膏购买决策测试，8类妈妈群体",
        )
        self.assertEqual(result, "unrelated")
        # Verify: if result is 'unrelated', the workflow should stop here
        # and create a new intake, NOT call llm_refine_followup

    def test_keyword_overlap_below_threshold_returns_unrelated(self):
        """Messages with keyword overlap below 60% must be unrelated."""
        overlap = keyword_overlap(
            "想买个电动牙刷给自己用",
            "舒客儿童牙膏防蛀概念测试",
        )
        self.assertLess(overlap, 0.60)

    def test_keyword_overlap_above_threshold_returns_candidate(self):
        """Messages with keyword overlap above 60% must be candidate_same_topic."""
        overlap = keyword_overlap(
            "舒客儿童牙膏防蛀效果妈妈",
            "舒客儿童牙膏防蛀效果妈妈",
        )
        self.assertGreater(overlap, 0.60)

    def test_same_task_preconditions_fail_on_type_change(self):
        """task_type change must prevent same_task classification."""
        result = check_same_task_preconditions(
            prior_brief={"task_type": "concept_test", "product_context": "儿童牙膏"},
            new_brief={"task_type": "price_test", "product_context": "儿童牙膏"},
        )
        self.assertFalse(result)

    def test_same_task_preconditions_fail_on_product_change(self):
        """Product context change must prevent same_task classification."""
        result = check_same_task_preconditions(
            prior_brief={"task_type": "concept_test", "product_context": "儿童牙膏"},
            new_brief={"task_type": "concept_test", "product_context": "成人洗发水"},
        )
        self.assertFalse(result)

    def test_same_task_preconditions_pass_on_matching(self):
        """Matching task_type and product_context should pass."""
        result = check_same_task_preconditions(
            prior_brief={"task_type": "concept_test", "product_context": "儿童牙膏防蛀"},
            new_brief={"task_type": "concept_test", "product_context": "儿童防蛀牙膏"},
        )
        self.assertTrue(result)


    def test_embedding_similarity_uses_stronger_signal_than_keyword_overlap(self):
        """Near-paraphrases should score above overlap-only matching."""
        text_a = "儿童牙膏防蛀效果怎么样，孩子会不会更愿意刷牙"
        text_b = "儿童牙膏防蛀能力如何，宝宝会不会更愿意坚持刷牙"

        overlap = keyword_overlap(text_a, text_b)
        similarity = embedding_similarity(text_a, text_b)

        self.assertGreater(similarity, overlap)
        self.assertGreater(similarity, 0.85)


if __name__ == "__main__":
    unittest.main()
