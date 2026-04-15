"""
CI Blocking Test: History Cannot Override Current Fact

Per testing-and-operations.md §test_history_cannot_override_current_fact.py:
Verify that historical snapshots cannot overwrite current BusinessBrief
fields without going through follow-up adjudication.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from business_brief import BusinessBrief
from followup_adjudicator import adjudicate_followup, check_same_task_preconditions
from task_session_manager import TaskSession, TaskSessionManager


def _persona_path() -> Path:
    return Path(__file__).resolve().parents[1] / "persona_samples_complete.json"


class TestHistoryCannotOverrideCurrentFact(unittest.TestCase):
    """Historical data must not override current facts without adjudication."""

    def test_prior_brief_does_not_auto_merge_into_new_session(self):
        """Starting a new task must clear all prior brief fields."""
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskSessionManager(
                session_dir=Path(tmp) / "sessions",
                persona_path=_persona_path(),
            )
            session = manager.get_or_create("g1", "c1", "u1")
            session.business_brief = {
                "task_type": "price_test",
                "product_context": "Old product",
                "research_goal": "Old goal",
                "price_test_mode": "absolute_price",
                "price_range": "29-39",
            }
            manager.save(session)

            # Start new task
            session = manager.start_new_task(session)

            self.assertIsNone(session.business_brief)
            self.assertIsNone(session.research_plan)
            self.assertIsNone(session.readiness_decision)

    def test_unrelated_followup_creates_fresh_intake_without_prior_data(self):
        """When follow-up is 'unrelated', no prior brief data should leak."""
        prior_brief = {
            "task_type": "concept_test",
            "product_context": "儿童牙膏防蛀配方",
            "research_goal": "评估概念吸引力",
        }
        prior_brief_text = json.dumps(prior_brief, ensure_ascii=False)
        candidate_brief_text = json.dumps({
            "task_type": "unknown",
            "product_context": "成人洗发水去屑",
            "research_goal": "评估去屑效果",
        }, ensure_ascii=False)

        result = adjudicate_followup(candidate_brief_text, prior_brief_text)
        self.assertEqual(result, "unrelated")

    def test_same_task_preconditions_reject_product_context_reversal(self):
        """Changing product_context must fail same_task preconditions."""
        prior_brief = {"task_type": "concept_test", "product_context": "儿童防蛀牙膏"}
        new_brief = {"task_type": "concept_test", "product_context": "成人美白牙膏"}

        self.assertFalse(check_same_task_preconditions(prior_brief, new_brief))

    def test_same_task_preconditions_reject_task_type_change(self):
        """Changing task_type must fail same_task preconditions."""
        prior_brief = {"task_type": "concept_test", "product_context": "儿童牙膏"}
        new_brief = {"task_type": "price_test", "product_context": "儿童牙膏"}

        self.assertFalse(check_same_task_preconditions(prior_brief, new_brief))

    def test_current_brief_fields_are_not_polluted_by_prior_snapshot(self):
        """Building a new BusinessBrief must only use current session fields."""
        session = TaskSession(
            session_id="s1", group_id="g1", conversation_id="c1", user_id="u1",
        )
        session.fields["question_type"]["status"] = "provided"
        session.fields["question_type"]["value"] = "copy_feedback"
        session.fields["user_question"]["status"] = "provided"
        session.fields["user_question"]["value"] = "Current question"
        session.fields["product_info"]["status"] = "provided"
        session.fields["product_info"]["value"] = "Current product"

        brief = BusinessBrief.from_session_fields(session.fields)

        # Brief must reflect CURRENT fields, not any historical data
        self.assertEqual(brief.research_goal, "Current question")
        self.assertEqual(brief.product_context, "Current product")


if __name__ == "__main__":
    unittest.main()
