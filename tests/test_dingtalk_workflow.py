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

    def _start_bot(self, temp_dir: str, report_publisher=None):
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
            ai_client=None,
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

    def test_multi_mode_can_run_and_return_report_paths(self):
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

    def test_completed_task_can_include_public_report_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class StubPublisher:
                def publish_report(self, html_report_path):
                    return {
                        "status": "published",
                        "public_report_url": "https://dingtalk-reports.vercel.app/qual-report.html",
                    }

            _, bot = self._start_bot(temp_dir, report_publisher=StubPublisher())
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

    def test_html_renderer_contains_qualitative_sections(self):
        renderer_module = self.load_renderer_module()
        sample_report = {
            "meta": {
                "mode": "multi",
                "question_type": "purchase_decision",
                "generated_at": "2026-03-11 20:00:00",
                "total_agents": 8,
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
                    "persona_name": "林可可",
                    "question_type": "purchase_decision",
                    "stance": "interested",
                    "core_needs": ["省心", "防蛀有效"],
                    "motivations": ["专业背书", "省时间"],
                    "concerns": ["表达是否可信"],
                    "decision_logic": "会先看证明材料，再决定要不要买。",
                    "verbatim_answer": "如果你能把专业依据讲清楚，我会愿意试。",
                    "confidence_note": "基于现有画像和当前提供信息生成。",
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
            "appendix": {
                "selected_persona": None,
                "follow_up_context": "",
                "attachments": [],
            },
        }

        html = renderer_module.HTMLReportRenderer().render(sample_report)

        self.assertIn("消费者原声", html)
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
