import importlib.util
import json
import threading
import time
import unittest
from pathlib import Path


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StubAIClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.is_configured = True

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        if not self.responses:
            raise AssertionError("No stub responses left")
        return self.responses.pop(0)


class ParallelProbeAIClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.is_configured = True
        self.supports_parallel_calls = True
        self.lock = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        with self.lock:
            self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
            if not self.responses:
                raise AssertionError("No stub responses left")
            response = self.responses.pop(0)

        time.sleep(0.05)

        with self.lock:
            self.inflight -= 1
        return response


class QualitativeResearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "qualitative_research.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_or_fail(self):
        if not self.module_path.exists():
            self.fail("qualitative_research.py is missing")
        return load_module("qualitative_research_under_test", self.module_path)

    def build_mom_response(self, persona_id: str, persona_name: str, stance: str = "hesitant"):
        return {
            "mode": "live_text",
            "text": json.dumps(
                {
                    "persona_id": persona_id,
                    "persona_name": persona_name,
                    "stance": stance,
                    "core_needs": ["safety", "clarity"],
                    "motivations": ["proof", "fit"],
                    "concerns": ["risk", "trust"],
                    "decision_logic": "needs proof first",
                    "verbatim_answer": f"{persona_name} wants clearer proof before buying.",
                    "evidence_trace": "Grounded in persona profile and brief.",
                },
                ensure_ascii=False,
            ),
        }

    def build_summary_response(self):
        return {
            "mode": "live_text",
            "text": json.dumps(
                {
                    "consensus": ["Most moms need clearer proof."],
                    "differences": ["Trust thresholds vary by persona."],
                    "pain_points": ["Hard to trust an unfamiliar promise."],
                    "drivers": ["Clear evidence and fit-for-child messaging."],
                    "barriers": ["Weak credibility."],
                    "copy_insights": ["Explain the causal logic behind the claim."],
                    "recommendations": ["Lead with one proven benefit and back it up."],
                },
                ensure_ascii=False,
            ),
        }

    def build_plan_response(
        self,
        *,
        question_type: str = "copy_feedback",
        recommended_mode: str = "multi",
        target_persona: str = "",
        is_runnable: bool = True,
        needs_clarification: bool = False,
        missing_information=None,
        clarification_questions=None,
        assumptions_if_run_now=None,
    ):
        return {
            "mode": "live_text",
            "text": json.dumps(
                {
                    "normalized_intent": "Assess whether the material can drive interest and purchase consideration.",
                    "question_type": question_type,
                    "recommended_mode": recommended_mode,
                    "target_persona": target_persona,
                    "research_objectives": ["Judge attraction", "Find the top concern"],
                    "evaluation_dimensions": ["appeal", "clarity", "trust"],
                    "required_materials": ["user_question", "product_info", "copy_material"],
                    "missing_information": list(missing_information or []),
                    "clarification_questions": list(clarification_questions or ["Please clarify the product category."]),
                    "assumptions_if_run_now": list(assumptions_if_run_now or []),
                    "is_runnable": is_runnable,
                    "needs_clarification": needs_clarification,
                },
                ensure_ascii=False,
            ),
        }

    def test_multi_mode_uses_planner_before_eight_mom_llm_calls_and_summary(self):
        module = self.load_or_fail()
        stub = StubAIClient(
            [
                self.build_plan_response(
                    question_type="copy_feedback",
                    recommended_mode="multi",
                    is_runnable=True,
                    needs_clarification=False,
                ),
                self.build_mom_response("M01", "Mom 1"),
                self.build_mom_response("M02", "Mom 2"),
                self.build_mom_response("M03", "Mom 3"),
                self.build_mom_response("M04", "Mom 4"),
                self.build_mom_response("M05", "Mom 5"),
                self.build_mom_response("M06", "Mom 6"),
                self.build_mom_response("M07", "Mom 7"),
                self.build_mom_response("M08", "Mom 8"),
                self.build_summary_response(),
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="copy_feedback",
                user_question="Which claim is more convincing?",
                copy_material="Claim A versus Claim B",
            )
        )

        self.assertEqual(len(stub.calls), 10)
        self.assertIn("research_plan", report)
        self.assertEqual(report["meta"]["planner_status"], "complete")
        self.assertEqual(report["meta"]["agent_count_expected"], 8)
        self.assertEqual(report["meta"]["agent_count_completed"], 8)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M01")
        self.assertEqual(report["consumer_voice"][-1]["persona_id"], "M08")
        self.assertIn("evidence_trace", report["consumer_voice"][0])

    def test_runner_returns_clarification_state_before_dispatching_moms(self):
        module = self.load_or_fail()
        stub = StubAIClient(
            [
                self.build_plan_response(
                    question_type="copy_feedback",
                    recommended_mode="multi",
                    is_runnable=False,
                    needs_clarification=True,
                    missing_information=["product_info"],
                    clarification_questions=["What product category is this for?"],
                    assumptions_if_run_now=["Assume this is a child toothpaste concept."],
                )
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="copy_feedback",
                user_question="Will moms trust this claim?",
                copy_material="Claim A versus Claim B",
            )
        )

        self.assertEqual(len(stub.calls), 1)
        self.assertEqual(report["meta"]["completion_status"], "clarification_required")
        self.assertEqual(report["meta"]["agent_count_expected"], 0)
        self.assertEqual(report["meta"]["agent_count_completed"], 0)
        self.assertEqual(report["research_plan"]["needs_clarification"], True)
        self.assertEqual(report["research_plan"]["clarification_questions"], ["What product category is this for?"])
        self.assertEqual(report["consumer_voice"], [])

    def test_runner_rejects_assumption_run_without_user_authorization(self):
        module = self.load_or_fail()
        stub = StubAIClient(
            [
                self.build_plan_response(
                    question_type="copy_feedback",
                    recommended_mode="multi",
                    is_runnable=False,
                    needs_clarification=True,
                    missing_information=["product_info"],
                    clarification_questions=["What product category is this for?"],
                    assumptions_if_run_now=["Assume this is a child toothpaste concept."],
                )
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="copy_feedback",
                user_question="Will moms trust this claim?",
                copy_material="Claim A versus Claim B",
                allow_assumption_run=False,
            )
        )

        self.assertEqual(report["meta"]["completion_status"], "clarification_required")
        self.assertFalse(report["meta"]["assumption_run"])

    def test_runner_raises_when_any_mom_agent_returns_fallback_mode(self):
        module = self.load_or_fail()
        stub = StubAIClient(
            [
                {
                    "mode": "fallback_text",
                    "text": "Fallback summary: remote text generation failed.",
                }
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        with self.assertRaises(module.IncompleteResearchRunError):
            runner.run(
                module.QualitativeResearchInput(
                    mode="single",
                    question_type="copy_feedback",
                    persona_id="M01",
                    user_question="Does this copy work?",
                    copy_material="Claim A versus Claim B",
                )
            )

    def test_runner_raises_on_persona_mismatch(self):
        module = self.load_or_fail()
        stub = StubAIClient([self.build_mom_response("M08", "Wrong Mom")])
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        with self.assertRaises(module.IncompleteResearchRunError):
            runner.run(
                module.QualitativeResearchInput(
                    mode="single",
                    question_type="purchase_decision",
                    persona_id="M01",
                    user_question="Would she buy this?",
                    product_info="A new product promise",
                )
            )

    def test_runner_raises_when_mom_output_introduces_unexpected_numeric_claim(self):
        module = self.load_or_fail()
        bad_response = self.build_mom_response("M03", "Mom 3")
        bad_payload = json.loads(bad_response["text"])
        bad_payload["verbatim_answer"] = "3天见效，听起来太夸张了。"
        bad_response["text"] = json.dumps(bad_payload, ensure_ascii=False)
        stub = StubAIClient([bad_response])
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        with self.assertRaises(module.IncompleteResearchRunError):
            runner.run(
                module.QualitativeResearchInput(
                    mode="single",
                    question_type="copy_feedback",
                    persona_id="M03",
                    user_question="对于卖点“穿上它，一年少去3次医院”，这位妈妈会不会被打动？",
                    copy_material="穿上它，一年少去3次医院",
                    product_info="一款主打减少孩子生病次数的儿童穿着类产品概念。",
                )
            )

    def test_multi_mode_executes_mom_agents_in_parallel_when_client_supports_it(self):
        module = self.load_or_fail()
        probe = ParallelProbeAIClient(
            [
                self.build_plan_response(
                    question_type="copy_feedback",
                    recommended_mode="multi",
                    is_runnable=True,
                    needs_clarification=False,
                ),
                self.build_mom_response("M01", "Mom 1"),
                self.build_mom_response("M02", "Mom 2"),
                self.build_mom_response("M03", "Mom 3"),
                self.build_mom_response("M04", "Mom 4"),
                self.build_mom_response("M05", "Mom 5"),
                self.build_mom_response("M06", "Mom 6"),
                self.build_mom_response("M07", "Mom 7"),
                self.build_mom_response("M08", "Mom 8"),
                self.build_summary_response(),
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=probe)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="copy_feedback",
                user_question="Which claim is more convincing?",
                copy_material="Claim A versus Claim B",
            )
        )

        self.assertEqual(report["meta"]["total_agents"], 8)
        self.assertGreater(probe.max_inflight, 1)

    def test_single_mode_research_assistant_prompt_requires_non_empty_consensus_and_differences(self):
        module = self.load_or_fail()
        assistant = module.ResearchAssistantAgent(StubAIClient([]))

        prompt = assistant._build_prompt(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M03",
                user_question="Will this claim convince her?",
                copy_material="Claim A versus Claim B",
            ),
            [
                {
                    "persona_id": "M03",
                    "persona_name": "Mom 3",
                    "question_type": "copy_feedback",
                    "stance": "hesitant",
                    "core_needs": ["safety"],
                    "motivations": ["proof"],
                    "concerns": ["trust"],
                    "decision_logic": "needs proof first",
                    "verbatim_answer": "I need more proof before buying.",
                    "evidence_trace": "Grounded in persona profile.",
                }
            ],
        )

        self.assertIn("single mode", prompt.lower())
        self.assertIn("do not leave consensus or differences empty", prompt.lower())
        self.assertIn("simplified chinese", prompt.lower())

    def test_mom_prompt_requires_chinese_output_and_numeric_claim_preservation(self):
        module = self.load_or_fail()
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=StubAIClient([]))
        persona = next(item for item in runner.personas if item["segment_id"] == "M03")
        agent = module.MomPersonaAgent(persona, StubAIClient([]))

        prompt = agent._build_prompt(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M03",
                user_question="对于卖点“穿上它，一年少去3次医院”，这位妈妈会不会被打动？",
                copy_material="穿上它，一年少去3次医院",
                product_info="一款主打减少孩子生病次数的儿童穿着类产品概念。",
            )
        )

        self.assertIn("write in simplified chinese", prompt.lower())
        self.assertIn("do not change any key numbers", prompt.lower())

    def test_multi_mode_returns_eight_mom_responses_and_summary(self):
        module = self.load_or_fail()
        stub = StubAIClient(
            [
                self.build_plan_response(
                    question_type="purchase_decision",
                    recommended_mode="multi",
                    is_runnable=True,
                    needs_clarification=False,
                ),
                self.build_mom_response("M01", "Mom 1"),
                self.build_mom_response("M02", "Mom 2"),
                self.build_mom_response("M03", "Mom 3"),
                self.build_mom_response("M04", "Mom 4"),
                self.build_mom_response("M05", "Mom 5"),
                self.build_mom_response("M06", "Mom 6"),
                self.build_mom_response("M07", "Mom 7"),
                self.build_mom_response("M08", "Mom 8"),
                self.build_summary_response(),
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="8类妈妈会不会买，最大的顾虑是什么？",
                product_info="儿童牙膏，主打低氟防蛀和孩子更愿意坚持刷牙。",
            )
        )

        self.assertEqual(report["meta"]["mode"], "multi")
        self.assertEqual(report["meta"]["question_type"], "purchase_decision")
        self.assertEqual(report["meta"]["total_agents"], 8)
        self.assertEqual(report["meta"]["agent_count_expected"], 8)
        self.assertEqual(report["meta"]["agent_count_completed"], 8)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertEqual(len(report["consumer_voice"]), 8)
        self.assertEqual(
            sorted(report["research_summary"].keys()),
            [
                "barriers",
                "consensus",
                "copy_insights",
                "differences",
                "drivers",
                "pain_points",
                "recommendations",
            ],
        )
        self.assertIn("user_question", report["research_brief"])
        self.assertIn("product_info", report["research_brief"])

        first_response = report["consumer_voice"][0]
        self.assertEqual(
            sorted(first_response.keys()),
            [
                "concerns",
                "core_needs",
                "decision_logic",
                "evidence_trace",
                "motivations",
                "persona_id",
                "persona_name",
                "question_type",
                "stance",
                "verbatim_answer",
            ],
        )

    def test_single_mode_returns_only_selected_persona(self):
        module = self.load_or_fail()
        stub = StubAIClient(
            [
                self.build_plan_response(
                    question_type="copy_feedback",
                    recommended_mode="single",
                    target_persona="M04",
                    is_runnable=True,
                    needs_clarification=False,
                ),
                self.build_mom_response("M04", "Mom 4"),
                self.build_summary_response(),
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=stub)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="高线忙碌妈会被哪句话打动？",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        self.assertEqual(report["meta"]["mode"], "single")
        self.assertEqual(report["meta"]["total_agents"], 1)
        self.assertEqual(report["meta"]["agent_count_expected"], 1)
        self.assertEqual(report["meta"]["agent_count_completed"], 1)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertEqual(len(report["consumer_voice"]), 1)
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M04")
        self.assertEqual(report["appendix"]["selected_persona"], "M04")
        self.assertTrue(report["research_summary"]["recommendations"])


if __name__ == "__main__":
    unittest.main()
