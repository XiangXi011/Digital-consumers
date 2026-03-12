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


class DingTalkWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.bot_path = cls.root / "dingtalk_bot.py"
        cls.renderer_path = cls.root / "html_report_renderer.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_bot_module(self):
        if not self.bot_path.exists():
            self.fail("dingtalk_bot.py is missing")
        return load_module("dingtalk_bot_under_test", self.bot_path)

    def load_renderer_module(self):
        if not self.renderer_path.exists():
            self.fail("html_report_renderer.py is missing")
        return load_module("html_report_renderer_under_test", self.renderer_path)

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
                    "normalized_intent": "Assess the request before interviewing mothers.",
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

    def build_success_ai_client(self):
        return StubAIClient(
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

    def _start_bot(self, temp_dir: str, report_publisher=None, ai_client=None):
        module = self.load_bot_module()
        publisher = report_publisher
        if publisher is None:
            class NullPublisher:
                def publish_report(self, html_report_path):
                    return {"status": "disabled", "public_report_url": ""}

            publisher = NullPublisher()
        bot = module.DingTalkBotWorkflow(
            persona_path=self.persona_path,
            session_dir=Path(temp_dir) / "sessions",
            output_dir=Path(temp_dir) / "outputs",
            ai_client=ai_client,
            report_publisher=publisher,
        )
        return module, bot

    def test_first_contact_returns_research_brief_checklist(self):
        module = self.load_bot_module()
        self.assertTrue(hasattr(module, "build_dingtalk_workflow_graph"))

        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                }
            )

        self.assertEqual(result["status"], "collecting")
        self.assertIn("研究任务信息清单", result["messages"][0]["content"])
        self.assertIn("模式", result["messages"][0]["content"])
        self.assertIn("研究问题", result["messages"][0]["content"])
        self.assertIn("用户问题", result["messages"][0]["content"])

    def test_single_mode_without_persona_requests_follow_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "单人模式，帮我看看这句文案有没有吸引力。",
                }
            )

        self.assertEqual(result["status"], "collecting")
        self.assertIn("指定妈妈画像", result["messages"][0]["content"])

    def test_planner_clarification_blocks_task_creation_until_user_answers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_client = StubAIClient(
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
            _, bot = self._start_bot(temp_dir, ai_client=ai_client)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@bot I want to run mom qualitative research",
                }
            )
            session = bot.session_manager.find_session_for("group-1", "conv-1", "user-1")
            bot.session_manager._set_field_value(session, "mode", "multi")
            bot.session_manager._set_field_value(session, "question_type", "copy_feedback")
            bot.session_manager._set_field_value(session, "user_question", "Will 8 moms find this copy attractive?")
            bot.session_manager.save(session)
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "run",
                }
            )

        self.assertEqual(result["status"], "awaiting_clarification")
        self.assertIsNone(result["task_id"])
        self.assertIn("What product category is this for?", result["messages"][0]["content"])

    def test_explicit_assumption_authorization_allows_first_pass_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_client = StubAIClient(
                [
                    self.build_plan_response(
                        question_type="copy_feedback",
                        recommended_mode="multi",
                        is_runnable=False,
                        needs_clarification=True,
                        missing_information=["product_info"],
                        clarification_questions=["What product category is this for?"],
                        assumptions_if_run_now=["Assume this is a child toothpaste concept."],
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
            _, bot = self._start_bot(temp_dir, ai_client=ai_client)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@bot I want to run mom qualitative research",
                }
            )
            session = bot.session_manager.find_session_for("group-1", "conv-1", "user-1")
            bot.session_manager._set_field_value(session, "mode", "multi")
            bot.session_manager._set_field_value(session, "question_type", "copy_feedback")
            bot.session_manager._set_field_value(session, "user_question", "Will 8 moms find this copy attractive?")
            bot.session_manager.save(session)
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "run once with assumptions",
                }
            )
            finished = bot.run_pending_task(start["task_id"])
            report = json.loads(Path(finished["json_report_path"]).read_text(encoding="utf-8"))

        self.assertEqual(start["status"], "running")
        self.assertTrue(start["task_id"])
        self.assertEqual(finished["status"], "completed")
        self.assertTrue(report["meta"]["assumption_run"])
        self.assertEqual(report["research_plan"]["clarification_questions"], ["What product category is this for?"])

    def test_multi_mode_can_run_and_return_report_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir, ai_client=self.build_success_ai_client())
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "模式：多人\n"
                        "研究问题：购买决策\n"
                        "用户问题：这款儿童牙膏 8 类妈妈会不会买，最大的顾虑是什么？\n"
                        "产品信息：低氟防蛀，孩子更愿意坚持刷牙。\n"
                    ),
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                }
            )
            finished = bot.run_pending_task(start["task_id"])
            self.assertTrue(Path(finished["html_report_path"]).exists())
            self.assertTrue(Path(finished["json_report_path"]).exists())
            report = json.loads(Path(finished["json_report_path"]).read_text(encoding="utf-8"))

        self.assertEqual(start["status"], "running")
        self.assertTrue(start["task_id"])
        self.assertEqual(finished["status"], "completed")
        self.assertIn("简版结论", finished["messages"][0]["content"])
        self.assertEqual(report["meta"]["mode"], "multi")
        self.assertEqual(report["meta"]["total_agents"], 8)
        self.assertEqual(report["meta"]["agent_count_expected"], 8)
        self.assertEqual(report["meta"]["agent_count_completed"], 8)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertIn("evidence_trace", report["consumer_voice"][0])

    def test_completed_task_can_include_public_report_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class StubPublisher:
                def publish_report(self, html_report_path):
                    return {
                        "status": "published",
                        "public_report_url": "https://dingtalk-reports.vercel.app/qual-report.html",
                    }

            _, bot = self._start_bot(
                temp_dir,
                report_publisher=StubPublisher(),
                ai_client=self.build_success_ai_client(),
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "模式：多人\n"
                        "研究问题：产品概念\n"
                        "用户问题：这个产品概念对 8 类妈妈有没有吸引力？\n"
                    ),
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                }
            )
            finished = bot.run_pending_task(start["task_id"])

        self.assertEqual(
            finished["public_report_url"],
            "https://dingtalk-reports.vercel.app/qual-report.html",
        )

    def test_incomplete_agent_run_returns_incomplete_message_without_report_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_client = StubAIClient(
                [
                    self.build_plan_response(
                        question_type="copy_feedback",
                        recommended_mode="single",
                        target_persona="M01",
                        is_runnable=True,
                        needs_clarification=False,
                    ),
                    {
                        "mode": "fallback_text",
                        "text": "Fallback summary: remote text generation failed.",
                    }
                ]
            )
            _, bot = self._start_bot(temp_dir, ai_client=ai_client)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "模式：单人\n"
                        "研究问题：文案和卖点反馈\n"
                        "指定妈妈画像：M01\n"
                        "用户问题：Does this claim work?\n"
                        "文案或卖点：Claim A versus Claim B\n"
                    ),
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                }
            )
            finished = bot.run_pending_task(start["task_id"])

        self.assertEqual(start["status"], "running")
        self.assertEqual(finished["status"], "error")
        self.assertEqual(finished["messages"][0]["content"], "本次结果不完整，请稍后重试")
        self.assertIsNone(finished["html_report_path"])
        self.assertIsNone(finished["json_report_path"])

    def test_same_group_different_users_have_independent_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            result_user_1 = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                }
            )
            result_user_2 = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-2",
                    "text": "@机器人 我也想做妈妈定性研究",
                }
            )
            session_user_1 = bot.session_manager.find_session_for("group-1", "conv-1", "user-1")
            session_user_2 = bot.session_manager.find_session_for("group-1", "conv-1", "user-2")

        self.assertEqual(result_user_1["status"], "collecting")
        self.assertEqual(result_user_2["status"], "collecting")
        self.assertIn("研究任务信息清单", result_user_1["messages"][0]["content"])
        self.assertIn("研究任务信息清单", result_user_2["messages"][0]["content"])
        self.assertNotEqual(session_user_1.session_id, session_user_2.session_id)

    def test_legacy_session_file_is_reset_to_qualitative_checklist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            session_dir = Path(temp_dir) / "sessions"
            session_dir.mkdir(parents=True, exist_ok=True)
            legacy_session = {
                "session_id": "group-1__conv-1__user-1",
                "group_id": "group-1",
                "conversation_id": "conv-1",
                "user_id": "user-1",
                "status": "completed",
                "checklist_sent": True,
                "partial_run_authorized": True,
                "fields": {
                    "concept_name": {
                        "label": "legacy concept name",
                        "priority": "P0",
                        "status": "provided",
                        "value": "legacy record",
                    }
                },
                "missing_fields": ["legacy missing field"],
                "last_task_id": "group-1__conv-1__user-1__run",
                "html_report_path": "C:/legacy/report.html",
                "json_report_path": "C:/legacy/report.json",
            }
            (session_dir / "group-1__conv-1__user-1.json").write_text(
                json.dumps(legacy_session, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "妈妈定性研究",
                }
            )

        self.assertEqual(result["status"], "collecting")
        self.assertIn("研究任务信息清单", result["messages"][0]["content"])
        self.assertIsNone(result["task_id"])

    def test_html_renderer_contains_qualitative_sections(self):
        renderer_module = self.load_renderer_module()
        sample_report = {
            "meta": {
                "mode": "multi",
                "question_type": "purchase_decision",
                "generated_at": "2026-03-12 20:00:00",
                "total_agents": 8,
                "agent_count_expected": 8,
                "agent_count_completed": 8,
                "completion_status": "complete",
            },
            "research_brief": {
                "user_question": "这款儿童牙膏 8 类妈妈会不会买，最大的顾虑是什么？",
                "product_info": "低氟防蛀，孩子更愿意坚持刷牙。",
                "copy_material": "专业防蛀，孩子喜欢，妈妈省心。",
                "background_material": "上市前定性预研究。",
            },
            "consumer_voice": [
                {
                    "persona_id": "M04",
                    "persona_name": "刘思涵",
                    "question_type": "purchase_decision",
                    "stance": "interested",
                    "core_needs": ["省心", "防蛀有效"],
                    "motivations": ["专业背书", "省时间"],
                    "concerns": ["表达是否可信"],
                    "decision_logic": "会先看证明材料，再决定要不要买。",
                    "verbatim_answer": "如果你能把专业依据讲清楚，我会愿意试。",
                    "evidence_trace": "Grounded in proof-seeking behavior.",
                }
            ],
            "research_summary": {
                "consensus": ["多数妈妈都会先看信息是否可信。"],
                "differences": ["高线妈妈更重证据，粗养妈妈更看简单直接。"],
                "pain_points": ["最大痛点是孩子不愿意坚持刷牙。"],
                "drivers": ["驱动主要来自清晰可感知的防蛀利益点。"],
                "barriers": ["障碍主要是卖点表达不够清楚。"],
                "copy_insights": ["要先讲核心利益，再补证明。"],
                "recommendations": ["先收敛成一个主卖点，再加两条辅助证明。"],
            },
            "research_plan": {
                "normalized_intent": "判断这款儿童牙膏概念对 8 类妈妈是否有购买吸引力。",
                "question_type": "purchase_decision",
                "recommended_mode": "multi",
                "target_persona": "",
                "research_objectives": ["判断会不会买", "识别最大顾虑"],
                "evaluation_dimensions": ["吸引力", "可信度", "防蛀利益点"],
                "required_materials": ["user_question", "product_info", "copy_material"],
                "missing_information": [],
                "clarification_questions": ["品牌是否为新品牌？"],
                "assumptions_if_run_now": ["默认这是一个新品品牌。"],
                "is_runnable": True,
                "needs_clarification": False,
            },
            "appendix": {
                "selected_persona": None,
                "follow_up_context": "",
                "attachments": [],
            },
        }

        html = renderer_module.HTMLReportRenderer().render(sample_report)

        self.assertIn("消费者原声", html)
        self.assertIn("任务拆解", html)
        self.assertIn("研究目标", html)
        self.assertIn("评估维度", html)
        self.assertIn("假设前提", html)
        self.assertIn("研究总结", html)
        self.assertIn("共识", html)
        self.assertIn("分歧", html)
        self.assertIn("痛点", html)
        self.assertIn("驱动", html)
        self.assertIn("障碍", html)
        self.assertIn("启发", html)
        self.assertIn("建议", html)
        self.assertNotIn("estimated_conversion_rate", html)
        self.assertNotIn("segment_opportunity", html)
        self.assertNotIn("purchase_intent", html)


if __name__ == "__main__":
    unittest.main()
