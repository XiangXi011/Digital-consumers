import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from task_session_manager import TaskSession, TaskSessionManager


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _persona_path() -> Path:
    return Path(__file__).resolve().parents[1] / "persona_samples_complete.json"


def planner_json() -> str:
    return json.dumps(
        {
            "task_breakdown": ["Clarify the business question"],
            "research_objectives": ["Assess purchase willingness"],
            "evaluation_dimensions": ["trust", "value"],
            "sub_questions_for_personas": ["Would you buy it?"],
            "required_information": ["goal", "product"],
            "missing_information": [],
            "clarifying_questions": [],
            "ready_to_dispatch": True,
            "dispatch_scope": "single",
            "target_personas": ["M04"],
            "planner_notes": ["Proceed with the typed brief only"],
        },
        ensure_ascii=False,
    )


def mom_json(persona_id: str) -> str:
    return json.dumps(
        {
            "persona_id": persona_id,
            "persona_name": f"{persona_id}-mom",
            "task_responses": [
                {"question": "Would you buy it?", "answer": "Only if the proof looks real."}
            ],
            "dimension_scores": [
                {"dimension": "trust", "judgement": "Needs clearer proof"}
            ],
            "stance": "hesitant",
            "efficacy_clarity": 3,
            "trust_signal": 2,
            "convenience": 4,
            "price_fit": 3,
            "triggered_veto_codes": [],
            "core_needs": ["proof"],
            "motivations": ["safety"],
            "concerns": ["trust gap"],
            "decision_logic": "Needs proof before purchase.",
            "verbatim_answer": "I need stronger proof first.",
            "evidence_trace": "Trust is the blocking factor.",
        },
        ensure_ascii=False,
    )


def synthesis_json() -> str:
    return json.dumps(
        {
            "research_summary": {
                "consensus": ["Trust is the primary decision driver."],
                "differences": ["Price sensitivity is secondary."],
                "pain_points": ["Weak proof"],
                "drivers": ["Clinical validation"],
                "barriers": ["Trust gap"],
                "copy_insights": ["Lead with evidence"],
                "recommendations": ["Rewrite the proof stack"],
            },
            "structured_recommendation": {
                "objective_answers": ["Users need stronger proof before buying."],
                "cross_persona_consensus": ["Trust dominates"],
                "cross_persona_differences": ["Price is a secondary filter"],
                "key_risks": ["Evidence remains thin"],
                "opportunity_areas": ["Make proof more concrete"],
                "recommended_actions": ["Add clinical proof points"],
                "copy_or_product_adjustments": ["Sharpen the hero claim"],
                "evidence_gaps": ["Missing usage proof"],
                "confidence_assessment": ["Directionally strong"],
            },
        },
        ensure_ascii=False,
    )


class StubAIClient:
    is_configured = True

    def __init__(self):
        self.responses = [
            {"mode": "live_text", "text": planner_json()},
            {"mode": "live_text", "text": mom_json("M04")},
            {"mode": "live_text", "text": synthesis_json()},
        ]

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        if not self.responses:
            raise AssertionError("StubAIClient ran out of responses")
        return self.responses.pop(0)


class FrozenSnapshotReplayConsistencyTest(unittest.TestCase):
    def test_frozen_snapshot_carries_version_bundle_and_stable_replay_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskSessionManager(
                session_dir=Path(tmp) / "sessions",
                persona_path=_persona_path(),
            )
            session = TaskSession(
                session_id="session-1",
                group_id="group-1",
                conversation_id="conv-1",
                user_id="user-1",
            )
            payload = {
                "business_brief": {
                    "task_type": "copy_feedback",
                    "product_context": "Kids toothpaste",
                    "research_goal": "Assess proof-first copy",
                }
            }

            first_ref = manager.save_frozen_snapshot(session, "dispatch", payload)
            second_ref = manager.save_frozen_snapshot(session, "dispatch", payload)

            first = json.loads(Path(first_ref).read_text(encoding="utf-8"))
            second = json.loads(Path(second_ref).read_text(encoding="utf-8"))

        self.assertEqual(first["kind"], "frozen")
        self.assertEqual(first["replay_signature"], second["replay_signature"])
        self.assertTrue(
            {
                "prompt_bundle_version",
                "persona_pack_version",
                "schema_version",
                "router_version",
                "synthesis_version",
                "scoring_engine_version",
            }.issubset(first["version_bundle"])
        )

    def test_report_meta_contains_version_bundle_and_evaluation_metrics(self):
        root = Path(__file__).resolve().parents[1]
        module = load_module("qualitative_research_snapshot_test", root / "qualitative_research.py")
        runner = module.QualitativeResearchRunner(_persona_path(), ai_client=StubAIClient())

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="Will this proof-first copy work?",
                product_info="Kids toothpaste",
                copy_material="Clinically proven cavity protection",
            )
        )

        version_bundle = report["meta"]["version_bundle"]
        metrics = report["meta"]["evaluation_metrics"]

        self.assertTrue(
            {
                "prompt_bundle_version",
                "persona_pack_version",
                "schema_version",
                "router_version",
                "synthesis_version",
                "scoring_engine_version",
            }.issubset(version_bundle)
        )
        self.assertTrue(
            {
                "success_full",
                "success_partial",
                "failed_recoverable",
                "failed_terminal",
                "routing_distribution",
                "route_confidence_distribution",
                "clarification_rate_by_task_type",
                "route_override_rate",
                "inter_persona_divergence_score",
                "minority_survival_rate",
                "purchase_intent_entropy",
                "repeated_phrase_rate",
                "pipeline_total_latency_ms",
                "per_persona_latency_ms",
            }.issubset(metrics)
        )
        self.assertGreater(metrics["pipeline_total_latency_ms"], 0)
        self.assertIn("M04", metrics["per_persona_latency_ms"])


if __name__ == "__main__":
    unittest.main()
