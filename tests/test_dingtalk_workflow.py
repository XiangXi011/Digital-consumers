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
            raise AssertionError("StubAIClient ran out of responses")
        return self.responses.pop(0)


def planner_json(
    *,
    ready_to_dispatch: bool,
    dispatch_scope: str,
    target_personas: list[str],
    missing_information: list[str] | None = None,
    clarifying_questions: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "task_breakdown": ["判断用户核心问题", "验证主要购买障碍"],
            "research_objectives": ["判断是否愿意购买", "定位主要障碍和打动点"],
            "evaluation_dimensions": ["信任", "价格", "效果理解"],
            "sub_questions_for_personas": ["你会不会买", "你最大的顾虑是什么"],
            "required_information": ["用户问题", "产品信息或文案"],
            "missing_information": missing_information or [],
            "clarifying_questions": clarifying_questions or [],
            "ready_to_dispatch": ready_to_dispatch,
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


class DingTalkWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.bot_path = cls.root / "dingtalk_bot.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_bot_module(self):
        if not self.bot_path.exists():
            self.fail("dingtalk_bot.py is missing")
        return load_module("dingtalk_bot_under_test", self.bot_path)

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
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                    "is_bot_mentioned": True,
                }
            )

        self.assertEqual(result["status"], "collecting")
        self.assertIn("研究任务信息清单", result["messages"][0]["content"])

    def test_planner_blocked_request_returns_clarification_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_client = StubAIClient(
                responses=[
                    {
                        "mode": "live_text",
                        "text": planner_json(
                            ready_to_dispatch=False,
                            dispatch_scope="multi",
                            target_personas=[f"M0{index}" for index in range(1, 9)],
                            missing_information=["产品信息"],
                            clarifying_questions=["请补充产品信息或核心卖点。"],
                        ),
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
                    "is_bot_mentioned": True,
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
                        "用户问题：8类妈妈会不会买，最大的顾虑是什么？\n"
                    ),
                    "is_bot_mentioned": True,
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                    "is_bot_mentioned": True,
                }
            )

        self.assertEqual(result["status"], "awaiting_clarification")
        self.assertIsNone(result["task_id"])
        self.assertIn("请补充产品信息或核心卖点", result["messages"][0]["content"])

    def test_multi_mode_can_run_and_return_report_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_client = StubAIClient(
                responses=[
                    {
                        "mode": "live_text",
                        "text": planner_json(
                            ready_to_dispatch=True,
                            dispatch_scope="multi",
                            target_personas=[f"M0{index}" for index in range(1, 9)],
                        ),
                    },
                    *[{"mode": "live_text", "text": mom_json(f"M0{index}")} for index in range(1, 9)],
                    {"mode": "live_text", "text": synthesis_json()},
                ]
            )
            _, bot = self._start_bot(temp_dir, ai_client=ai_client)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                    "is_bot_mentioned": True,
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
                    "is_bot_mentioned": True,
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                    "is_bot_mentioned": True,
                }
            )
            finished = bot.run_pending_task(start["task_id"])
            html_exists = Path(finished["html_report_path"]).exists()
            json_exists = Path(finished["json_report_path"]).exists()
            report = json.loads(Path(finished["json_report_path"]).read_text(encoding="utf-8"))

        self.assertEqual(start["status"], "running")
        self.assertTrue(start["task_id"])
        self.assertEqual(finished["status"], "completed")
        self.assertTrue(html_exists)
        self.assertTrue(json_exists)
        self.assertEqual(report["meta"]["mode"], "multi")
        self.assertEqual(report["meta"]["total_agents"], 8)
        self.assertEqual(report["meta"]["agent_count_expected"], 8)
        self.assertEqual(report["meta"]["agent_count_completed"], 8)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertIn("research_plan", report)
        self.assertIn("structured_recommendation", report)

    def test_completed_task_can_include_public_report_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class StubPublisher:
                def publish_report(self, html_report_path):
                    return {
                        "status": "published",
                        "public_report_url": "https://dingtalk-reports.vercel.app/qual-report.html",
                    }

            ai_client = StubAIClient(
                responses=[
                    {
                        "mode": "live_text",
                        "text": planner_json(
                            ready_to_dispatch=True,
                            dispatch_scope="multi",
                            target_personas=[f"M0{index}" for index in range(1, 9)],
                        ),
                    },
                    *[{"mode": "live_text", "text": mom_json(f"M0{index}")} for index in range(1, 9)],
                    {"mode": "live_text", "text": synthesis_json()},
                ]
            )
            _, bot = self._start_bot(temp_dir, report_publisher=StubPublisher(), ai_client=ai_client)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                    "is_bot_mentioned": True,
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
                        "产品信息：专业防蛀，孩子喜欢，妈妈省心。\n"
                    ),
                    "is_bot_mentioned": True,
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                    "is_bot_mentioned": True,
                }
            )
            finished = bot.run_pending_task(start["task_id"])

        self.assertEqual(
            finished["public_report_url"],
            "https://dingtalk-reports.vercel.app/qual-report.html",
        )

    def test_failed_agent_run_returns_incomplete_result_message(self):
        class FailingAIClient:
            is_configured = True

            def __init__(self):
                self.calls = 0

            def generate_text(self, prompt: str, system_prompt: str | None = None):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "mode": "live_text",
                        "text": planner_json(
                            ready_to_dispatch=True,
                            dispatch_scope="multi",
                            target_personas=[f"M0{index}" for index in range(1, 9)],
                        ),
                    }
                return {"mode": "fallback_text", "text": "fallback"}

        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir, ai_client=FailingAIClient())
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我想做妈妈定性研究",
                    "is_bot_mentioned": True,
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
                    "is_bot_mentioned": True,
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按当前信息运行",
                    "is_bot_mentioned": True,
                }
            )
            finished = bot.run_pending_task(start["task_id"])

        self.assertEqual(finished["status"], "error")
        self.assertEqual(finished["messages"][0]["content"], "本次结果不完整，请稍后重试")
        self.assertIsNone(finished["html_report_path"])
        self.assertIsNone(finished["json_report_path"])


if __name__ == "__main__":
    unittest.main()
