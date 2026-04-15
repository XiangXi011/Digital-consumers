import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def planner_json(dispatch_scope: str, target_personas: list[str]) -> str:
    return json.dumps(
        {
            "task_breakdown": ["判断用户核心问题", "验证主要购买障碍"],
            "research_objectives": ["判断是否愿意购买", "定位主要障碍和打动点"],
            "evaluation_dimensions": ["信任", "价格", "效果理解"],
            "sub_questions_for_personas": ["你会不会买", "你最大的顾虑是什么"],
            "required_information": ["用户问题", "产品信息或文案"],
            "missing_information": [],
            "clarifying_questions": [],
            "ready_to_dispatch": True,
            "dispatch_scope": dispatch_scope,
            "target_personas": target_personas,
            "planner_notes": ["先围绕信任与效果理解收集反馈"],
        },
        ensure_ascii=False,
    )


def mom_json(persona_id: str) -> str:
    return json.dumps(
        {
            "persona_id": persona_id,
            "persona_name": f"{persona_id}-mom",
            "task_responses": [
                {"question": "你会不会买", "answer": "如果证据清楚我会尝试"},
                {"question": "你最大的顾虑是什么", "answer": "怕说得太笼统"},
            ],
            "dimension_scores": [
                {"dimension": "信任", "judgement": "需要更强证据"},
                {"dimension": "效果理解", "judgement": "卖点还不够具体"},
            ],
            "stance": "interested",
            "efficacy_clarity": 4,
            "trust_signal": 3,
            "convenience": 4,
            "price_fit": 3,
            "triggered_veto_codes": [],
            "core_needs": ["安全可靠", "省心"],
            "motivations": ["专业背书", "孩子愿意接受"],
            "concerns": ["价格是否合理"],
            "decision_logic": "先看证据，再判断是否值得尝试。",
            "verbatim_answer": "如果证据充分，我愿意试试。",
            "evidence_trace": "重视专业背书和孩子接受度。",
        },
        ensure_ascii=False,
    )


def synthesis_json() -> str:
    return json.dumps(
        {
            "research_summary": {
                "consensus": ["大多数妈妈先看可信证据。"],
                "differences": ["价格敏感度存在差异。"],
                "pain_points": ["担心效果说不清。"],
                "drivers": ["专业证明和孩子接受度。"],
                "barriers": ["价格和信任门槛。"],
                "copy_insights": ["先讲核心利益，再给证明。"],
                "recommendations": ["收敛单一卖点并补证据。"],
            },
            "structured_recommendation": {
                "objective_answers": ["妈妈会先验证可信度，再考虑购买。"],
                "cross_persona_consensus": ["信任和效果理解最关键。"],
                "cross_persona_differences": ["部分人群更看重价格。"],
                "key_risks": ["证据不足会直接抬高怀疑。"],
                "opportunity_areas": ["用更具体的结果证明建立信任。"],
                "recommended_actions": ["重写首屏卖点并补充可验证证据。"],
                "copy_or_product_adjustments": ["弱化空泛表达，强化专业证明。"],
                "evidence_gaps": ["缺真实用户体验或实验依据。"],
                "confidence_assessment": ["结论方向明确，但证据仍需加强。"],
            },
        },
        ensure_ascii=False,
    )


class SmartStubAIClient:
    is_configured = True

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        lowered = (system_prompt or "").lower()
        if "planner" in lowered:
            if "指定画像: M04" in prompt:
                return {"mode": "live_text", "text": planner_json("single", ["M04"])}
            return {
                "mode": "live_text",
                "text": planner_json("multi", [f"M0{index}" for index in range(1, 9)]),
            }
        if "synthesizer" in lowered:
            return {"mode": "live_text", "text": synthesis_json()}

        for persona_id in [f"M0{index}" for index in range(1, 9)]:
            if f"persona_id 必须是 {persona_id}" in prompt:
                return {"mode": "live_text", "text": mom_json(persona_id)}
        return {"mode": "live_text", "text": mom_json("M04")}


class FailingAIClient:
    is_configured = True

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        lowered = (system_prompt or "").lower()
        if "planner" in lowered:
            return {
                "mode": "live_text",
                "text": json.dumps(
                    {
                        "task_breakdown": ["判断用户核心问题"],
                        "research_objectives": ["判断是否愿意购买"],
                        "evaluation_dimensions": ["信任"],
                        "sub_questions_for_personas": ["你会不会买"],
                        "required_information": ["产品信息"],
                        "missing_information": ["产品信息"],
                        "clarifying_questions": ["请补充产品信息。"],
                        "ready_to_dispatch": False,
                        "dispatch_scope": "multi",
                        "target_personas": [f"M0{index}" for index in range(1, 9)],
                        "planner_notes": ["资料不足"],
                    },
                    ensure_ascii=False,
                ),
            }
        return {"mode": "fallback_text", "text": "fallback"}


class QualitativeRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "run_qualitative_regression.py"
        cls.renderer_path = cls.root / "html_report_renderer.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_regression_module(self):
        if not self.module_path.exists():
            self.fail("run_qualitative_regression.py is missing")
        return load_module("qualitative_regression_under_test", self.module_path)

    def load_renderer_module(self):
        if not self.renderer_path.exists():
            self.fail("html_report_renderer.py is missing")
        return load_module("html_report_renderer_under_test", self.renderer_path)

    def _write_golden_set(self, folder: Path) -> Path:
        golden_path = folder / "golden.json"
        golden_path.write_text(
            json.dumps(
                [
                    {
                        "id": "multi-copy-feedback",
                        "input": {
                            "mode": "multi",
                            "question_type": "copy_feedback",
                            "user_question": "这套文案对 8 类妈妈分别会产生什么反应？",
                            "copy_material": "专业防蛀，孩子喜欢，妈妈省心。",
                        },
                        "expected": {"mode": "multi", "agent_count": 8},
                    },
                    {
                        "id": "single-copy-feedback",
                        "input": {
                            "mode": "single",
                            "question_type": "copy_feedback",
                            "persona_id": "M04",
                            "user_question": "高线忙碌妈妈会被哪句话打动？",
                            "copy_material": "专业防蛀，孩子喜欢，妈妈省心。",
                        },
                        "expected": {"mode": "single", "agent_count": 1, "persona_id": "M04"},
                    },
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return golden_path

    def _sample_report(self) -> dict:
        return {
            "meta": {
                "mode": "multi",
                "question_type": "purchase_decision",
                "generated_at": "2026-03-12 14:00:00",
                "total_agents": 8,
                "agent_count_expected": 8,
                "agent_count_completed": 8,
                "completion_status": "complete",
                "schema_version": "qualitative-report-v2",
                "system_fingerprint": {
                    "git_sha": "test-sha",
                    "env": "test",
                    "model_id": "stub-model",
                    "prompt_version": "qualitative-prompt-v1",
                },
            },
            "research_brief": {
                "user_question": "8类妈妈会不会买？",
                "product_info": "儿童牙膏，低氟防蛀。",
                "copy_material": "专业防蛀，孩子喜欢，妈妈省心。",
                "background_material": "",
            },
            "research_plan": json.loads(planner_json("multi", [f"M0{index}" for index in range(1, 9)])),
            "consumer_voice": [json.loads(mom_json("M01"))],
            "research_summary": json.loads(synthesis_json())["research_summary"],
            "structured_recommendation": json.loads(synthesis_json())["structured_recommendation"],
            "appendix": {
                "selected_persona": None,
                "follow_up_context": "",
                "attachments": [],
            },
        }

    def test_regression_runner_writes_metrics_json(self):
        module = self.load_regression_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            golden_path = self._write_golden_set(temp_path)
            output_path = temp_path / "regression.json"

            exit_code = module.run_regression(
                golden_set_path=golden_path,
                output_path=output_path,
                persona_path=self.persona_path,
                ai_client=SmartStubAIClient(),
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["summary"]["case_count"], 2)
        self.assertEqual(payload["summary"]["completion_rate"], 1.0)
        self.assertEqual(payload["summary"]["schema_valid_rate"], 1.0)
        self.assertEqual(payload["summary"]["persona_match_rate"], 1.0)
        self.assertTrue(payload["summary"]["gate_passed"])

    def test_regression_runner_returns_nonzero_when_planner_blocks_execution(self):
        module = self.load_regression_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            golden_path = self._write_golden_set(temp_path)
            output_path = temp_path / "regression.json"

            exit_code = module.run_regression(
                golden_set_path=golden_path,
                output_path=output_path,
                persona_path=self.persona_path,
                ai_client=FailingAIClient(),
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertNotEqual(exit_code, 0)
        self.assertEqual(payload["summary"]["completion_rate"], 0.0)
        self.assertFalse(payload["summary"]["gate_passed"])

    def test_html_renderer_includes_planning_and_structured_recommendation_sections(self):
        module = self.load_renderer_module()
        renderer = module.HTMLReportRenderer()

        html = renderer.render(self._sample_report())

        self.assertIn("任务拆解", html)
        self.assertIn("研究目标", html)
        self.assertIn("结构化建议", html)
        self.assertIn("妈妈会先验证可信度，再考虑购买", html)


if __name__ == "__main__":
    unittest.main()
