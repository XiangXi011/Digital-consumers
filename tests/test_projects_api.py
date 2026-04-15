import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dingtalk_bot import DingTalkBotWorkflow
from routers import projects


def planner_json() -> str:
    return json.dumps(
        {
            "task_breakdown": ["Clarify purchase intent"],
            "research_objectives": ["Decide whether moms would buy"],
            "evaluation_dimensions": ["trust", "clarity", "fit"],
            "sub_questions_for_personas": ["Would you buy this?"],
            "required_information": ["user_question", "product_info_or_copy_material"],
            "missing_information": [],
            "clarifying_questions": [],
            "ready_to_dispatch": True,
            "dispatch_scope": "multi",
            "target_personas": [f"M0{index}" for index in range(1, 9)],
            "planner_notes": ["Use the default eight-mom pack."],
        },
        ensure_ascii=False,
    )


def mom_json(persona_id: str) -> str:
    return json.dumps(
        {
            "persona_id": persona_id,
            "persona_name": f"{persona_id}-mom",
            "task_responses": [
                {"question": "Would you buy this?", "answer": "Yes, if the proof is credible."}
            ],
            "dimension_scores": [
                {"dimension": "trust", "judgement": "Needs stronger proof"}
            ],
            "stance": "interested",
            "efficacy_clarity": 4,
            "trust_signal": 3,
            "convenience": 4,
            "price_fit": 3,
            "triggered_veto_codes": [],
            "core_needs": ["Safety"],
            "motivations": ["Clinical proof"],
            "concerns": ["Evidence quality"],
            "decision_logic": "Proof first, then purchase.",
            "verbatim_answer": "Show me stronger proof and I would buy it.",
            "evidence_trace": "Values trusted proof.",
        },
        ensure_ascii=False,
    )


def synthesis_json() -> str:
    return json.dumps(
        {
            "research_summary": {
                "consensus": ["Proof is the main unlock."],
                "differences": ["Price sensitivity varies."],
                "pain_points": ["Weak evidence."],
                "drivers": ["Clinical validation."],
                "barriers": ["Trust gap."],
                "copy_insights": ["Lead with proof."],
                "recommendations": ["Sharpen the hero claim."],
            },
            "structured_recommendation": {
                "objective_answers": ["Moms need clearer proof before purchase."],
                "cross_persona_consensus": ["Trust dominates."],
                "cross_persona_differences": ["Price fit varies by segment."],
                "key_risks": ["Evidence is too thin."],
                "opportunity_areas": ["Add stronger validation cues."],
                "recommended_actions": ["Rewrite the hero message with proof."],
                "copy_or_product_adjustments": ["Replace vague claims with evidence."],
                "evidence_gaps": ["No user study attached."],
                "confidence_assessment": ["Directionally strong."],
            },
        },
        ensure_ascii=False,
    )


class StubAIClient:
    is_configured = True

    def __init__(self, responses):
        self.responses = list(responses)

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        if not self.responses:
            raise AssertionError("StubAIClient ran out of responses")
        return self.responses.pop(0)


class NullPublisher:
    def publish_report(self, html_report_path):
        return {"status": "disabled", "public_report_url": ""}


class ProjectsApiTest(unittest.TestCase):
    def test_execute_project_run_completes_web_project_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_dir = temp_path / "sessions"
            output_dir = temp_path / "outputs"
            original_sessions_dir = projects.SESSIONS_DIR
            original_outputs_dir = projects.OUTPUTS_DIR
            original_workflow = projects._WEB_WORKFLOW
            try:
                projects.SESSIONS_DIR = session_dir
                projects.OUTPUTS_DIR = output_dir
                projects._WEB_WORKFLOW = None

                summary = projects.create_project(
                    projects.CreateProjectRequest(
                        name="Kids toothpaste concept",
                        project_type="copywriting",
                        product_info="Kids toothpaste with clinical proof",
                        copy_material="Low fluoride\nBetter taste",
                        user_question="Will moms buy this?",
                        mode="multi",
                    )
                )

                workflow = DingTalkBotWorkflow(
                    persona_path=Path(__file__).resolve().parents[1] / "persona_samples_complete.json",
                    session_dir=session_dir,
                    output_dir=output_dir,
                    ai_client=StubAIClient(
                        [
                            {"mode": "live_text", "text": planner_json()},
                            *[
                                {"mode": "live_text", "text": mom_json(f"M0{index}")}
                                for index in range(1, 9)
                            ],
                            {"mode": "live_text", "text": synthesis_json()},
                        ]
                    ),
                    report_publisher=NullPublisher(),
                )

                projects._execute_project_run(summary.session_id, workflow=workflow)
                payload = projects._load_session_data(summary.session_id)

                self.assertIsNotNone(payload)
                self.assertEqual(payload["status"], "completed")
                self.assertTrue(payload["html_report_path"])
                self.assertTrue(payload["json_report_path"])
                self.assertTrue(Path(payload["html_report_path"]).exists())
                self.assertTrue(Path(payload["json_report_path"]).exists())
            finally:
                projects.SESSIONS_DIR = original_sessions_dir
                projects.OUTPUTS_DIR = original_outputs_dir
                projects._WEB_WORKFLOW = original_workflow
