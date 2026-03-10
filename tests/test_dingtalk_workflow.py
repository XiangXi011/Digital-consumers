import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DingTalkWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.renderer_path = cls.root / "html_report_renderer.py"
        cls.bot_path = cls.root / "dingtalk_bot.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_bot_module(self):
        if not self.bot_path.exists():
            self.fail("dingtalk_bot.py is missing")
        return load_module("dingtalk_bot_under_test", self.bot_path)

    def load_renderer_module(self):
        if not self.renderer_path.exists():
            self.fail("html_report_renderer.py is missing")
        return load_module("html_report_renderer_under_test", self.renderer_path)

    def _start_bot(self, temp_dir: str, ai_client=None, report_publisher=None):
        module = self.load_bot_module()
        if ai_client is None:
            class OfflineAIClient:
                def generate_text(self, prompt, system_prompt=None):
                    return {"mode": "fallback_text", "text": "Offline summary"}

                def analyze_image(self, image_path, prompt):
                    return {
                        "mode": "fallback_vision",
                        "text": "Offline packaging summary for tests.",
                        "structured_signals": {"clarity": "unknown"},
                    }

                def extract_product_fields_from_image(self, image_path):
                    return {"mode": "fallback_extraction", "fields": {}}

                def generate_consumer_quote(self, payload):
                    return {"mode": "fallback_quote", "quote": ""}

                def validate_consumer_quote(self, expected_stance, expected_reason_tag, quote):
                    return {
                        "mode": "fallback_validation",
                        "is_consistent": False,
                        "detected_stance": "",
                        "detected_reason": "",
                        "why": "offline test client",
                    }

            ai_client = OfflineAIClient()
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

    def test_first_contact_returns_full_checklist(self):
        module = self.load_bot_module()
        self.assertTrue(hasattr(module, "build_dingtalk_workflow_graph"))

        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            self.assertTrue(hasattr(bot, "graph"))
            self.assertIsNotNone(bot.graph)
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )

        self.assertEqual(result["status"], "collecting")
        self.assertIn("完整资料清单", result["messages"][0]["content"])
        self.assertIn("产品/方案名称", result["messages"][0]["content"])

    def test_partial_information_triggers_missing_follow_up_and_run_question(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                        "品牌：舒客\n"
                        "品类：儿童口腔护理\n"
                        "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                        "价格：未定\n"
                        "包装信息：未定\n"
                    ),
                }
            )

        self.assertEqual(result["status"], "awaiting_run_confirmation")
        self.assertIn("还缺以下信息", result["messages"][0]["content"])
        self.assertIn("是否按当前已知信息先运行分析", result["messages"][0]["content"])

    def test_explicit_partial_run_confirmation_starts_analysis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                        "品牌：舒客\n"
                        "品类：儿童口腔护理\n"
                        "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                        "价格：39.9元\n"
                        "包装信息：卡通水果视觉，突出年龄段和防蛀卖点。\n"
                    ),
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按现有资料运行",
                }
            )

        self.assertEqual(result["status"], "running")
        self.assertIn("开始分析", result["messages"][0]["content"])
        self.assertTrue(result["task_id"])

    def test_completed_task_returns_summary_and_html_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                        "品牌：舒客\n"
                        "品类：儿童口腔护理\n"
                        "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                        "价格：39.9元\n"
                        "包装信息：卡通水果视觉，突出年龄段和防蛀卖点。\n"
                    ),
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按现有资料运行",
                }
            )
            finished = bot.run_pending_task(start["task_id"])
            self.assertEqual(finished["status"], "completed")
            self.assertIn("简版结论", finished["messages"][0]["content"])
            self.assertIn("当前建议", finished["messages"][0]["content"])
            self.assertNotIn("Current recommendation", finished["messages"][0]["content"])
            self.assertTrue(Path(finished["html_report_path"]).exists())
            self.assertTrue(Path(finished["json_report_path"]).exists())

    def test_completed_task_can_include_public_report_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class StubPublisher:
                def publish_report(self, html_report_path):
                    return {
                        "status": "published",
                        "public_report_url": "https://dingtalk-reports.vercel.app/sample-report.html",
                    }

            _, bot = self._start_bot(temp_dir, report_publisher=StubPublisher())
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                        "品牌：舒客\n"
                        "品类：儿童口腔护理\n"
                        "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                        "价格：39.9元\n"
                        "包装信息：卡通水果视觉，突出年龄段和防蛀卖点。\n"
                    ),
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按现有资料运行",
                }
            )
            finished = bot.run_pending_task(start["task_id"])

        self.assertEqual(finished["public_report_url"], "https://dingtalk-reports.vercel.app/sample-report.html")

    def test_image_attachment_can_replace_packaging_text_for_running(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "packaging.png"
            Image.new("RGB", (64, 64), color=(255, 120, 80)).save(image_path)
            _, bot = self._start_bot(temp_dir)

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                        "品牌：舒客\n"
                        "品类：儿童口腔护理\n"
                        "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                        "价格：39.9元\n"
                    ),
                    "attachments": [str(image_path)],
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按现有资料运行",
                }
            )

        self.assertEqual(result["status"], "running")

    def test_image_attachment_can_extract_core_fields_before_follow_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "detail-page.png"
            Image.new("RGB", (96, 200), color=(245, 245, 255)).save(image_path)

            class StubAIClient:
                def extract_product_fields_from_image(self, image_path):
                    return {
                        "mode": "stub_extraction",
                        "fields": {
                            "concept_name": "舒客儿童防蛀牙膏",
                            "brand": "舒客",
                            "category": "儿童牙膏",
                            "core_claims": ["健白净齿", "12小时长效防蛀", "4效组合防蛀证据"],
                            "price": "39.9元",
                            "packaging_summary": "蓝粉渐变儿童牙膏包装，正面突出防蛀功效和实验数据。",
                            "slogan": "健白净齿因子",
                            "ingredients": ["健白净齿因子"],
                            "detail_copy": "12小时长效防蛀，4效组合防蛀证据。",
                        },
                    }

            _, bot = self._start_bot(temp_dir, ai_client=StubAIClient())

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "",
                    "attachments": [str(image_path)],
                }
            )

        self.assertEqual(result["status"], "awaiting_run_confirmation")
        self.assertIn("舒客儿童防蛀牙膏", result["messages"][0]["content"])
        self.assertIn("儿童牙膏", result["messages"][0]["content"])
        self.assertIn("39.9元", result["messages"][0]["content"])
        self.assertIn("健白净齿；12小时长效防蛀；4效组合防蛀证据", result["messages"][0]["content"])
        missing_section = result["messages"][0]["content"].split("还缺以下信息：", 1)[1]
        self.assertNotIn("产品/方案名称", missing_section)
        self.assertNotIn("品类", missing_section)
        self.assertNotIn("核心卖点/功能点", missing_section)
        self.assertNotIn("价格或预计价格带", missing_section)
        self.assertNotIn("包装信息", missing_section)

    def test_text_fields_override_image_extracted_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "detail-page.png"
            Image.new("RGB", (96, 200), color=(245, 245, 255)).save(image_path)

            class StubAIClient:
                def extract_product_fields_from_image(self, image_path):
                    return {
                        "mode": "stub_extraction",
                        "fields": {
                            "concept_name": "图片识别旧名称",
                            "category": "图片识别旧品类",
                            "core_claims": ["图片卖点A", "图片卖点B"],
                            "price": "29.9元",
                            "packaging_summary": "图片包装描述",
                        },
                    }

            _, bot = self._start_bot(temp_dir, ai_client=StubAIClient())

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "产品/方案名称：人工修正名称\n品类：人工修正品类\n价格：39.9元",
                    "attachments": [str(image_path)],
                }
            )

        self.assertIn("人工修正名称", result["messages"][0]["content"])
        self.assertIn("人工修正品类", result["messages"][0]["content"])
        self.assertIn("39.9元", result["messages"][0]["content"])
        self.assertNotIn("图片识别旧名称", result["messages"][0]["content"])
        self.assertNotIn("图片识别旧品类", result["messages"][0]["content"])

    def test_natural_language_follow_up_updates_price_and_channels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客宝贝魔法变色儿童牙膏\n"
                        "品牌：舒客宝贝\n"
                        "品类：儿童牙膏/口腔护理\n"
                        "核心卖点：健白抗糖防蛀；12小时长效防蛀；超20项安全测试\n"
                        "包装信息：软管包装，突出魔法变色和防蛀。\n"
                    ),
                }
            )
            result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 价格28块钱一支 目标渠道线下和京东",
                }
            )

        self.assertEqual(result["status"], "awaiting_run_confirmation")
        self.assertIn("28块钱一支", result["messages"][0]["content"])
        self.assertIn("线下和京东", result["messages"][0]["content"])
        missing_section = result["messages"][0]["content"].split("还缺以下信息：", 1)[1]
        self.assertNotIn("价格或预计价格带", missing_section)
        self.assertNotIn("目标渠道", missing_section)
        self.assertIn("竞品/替代方案", missing_section)

    def test_same_group_different_users_have_independent_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)

            result_user_1 = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            result_user_2 = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-2",
                    "text": "@机器人 我也要做新品测试",
                }
            )

            session_user_1 = bot.session_manager.find_session_for("group-1", "conv-1", "user-1")
            session_user_2 = bot.session_manager.find_session_for("group-1", "conv-1", "user-2")

        self.assertEqual(result_user_1["status"], "collecting")
        self.assertEqual(result_user_2["status"], "collecting")
        self.assertIn("完整资料清单", result_user_1["messages"][0]["content"])
        self.assertIn("完整资料清单", result_user_2["messages"][0]["content"])
        self.assertNotEqual(session_user_1.session_id, session_user_2.session_id)

    def test_reset_command_clears_only_current_users_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, bot = self._start_bot(temp_dir)

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：用户一原任务\n"
                        "品类：儿童牙膏\n"
                        "核心卖点：防蛀；安全\n"
                        "价格：29元\n"
                        "包装信息：蓝白包装\n"
                    ),
                }
            )

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-2",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-2",
                    "text": (
                        "产品/方案名称：用户二保留任务\n"
                        "品类：儿童牙膏\n"
                        "核心卖点：趣味刷牙；防蛀\n"
                        "价格：31元\n"
                        "包装信息：粉紫包装\n"
                    ),
                }
            )

            reset_result = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "新任务",
                }
            )
            user_1_follow_up = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "价格：35元",
                }
            )
            user_2_follow_up = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-2",
                    "text": "目标渠道：京东",
                }
            )

        self.assertEqual(reset_result["status"], "collecting")
        self.assertIn("已为你清空当前群里的当前任务", reset_result["messages"][0]["content"])
        self.assertIn("完整资料清单", reset_result["messages"][0]["content"])
        self.assertNotIn("用户一原任务", user_1_follow_up["messages"][0]["content"])
        self.assertIn("用户二保留任务", user_2_follow_up["messages"][0]["content"])

    def test_completed_task_includes_packaging_review_when_image_is_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "packaging.png"
            Image.new("RGB", (64, 64), color=(255, 120, 80)).save(image_path)
            output_dir = Path(temp_dir) / "outputs"
            _, bot = self._start_bot(temp_dir)

            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "@机器人 我要做新品测试",
                }
            )
            bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": (
                        "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                        "品牌：舒客\n"
                        "品类：儿童口腔护理\n"
                        "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                        "价格：39.9元\n"
                    ),
                    "attachments": [str(image_path)],
                }
            )
            start = bot.handle_message(
                {
                    "group_id": "group-1",
                    "conversation_id": "conv-1",
                    "user_id": "user-1",
                    "text": "按现有资料运行",
                }
            )
            finished = bot.run_pending_task(start["task_id"])
            report = json.loads(Path(finished["json_report_path"]).read_text(encoding="utf-8"))

        self.assertIn("packaging_review", report["appendix"])
        self.assertEqual(report["input_summary"]["packaging_image_path"], str(image_path))

    def test_html_renderer_contains_key_visual_sections(self):
        renderer_module = self.load_renderer_module()
        sample_report = {
            "meta": {
                "concept_name": "舒客儿童益生菌防蛀牙膏概念版",
                "brand": "舒客",
                "generated_at": "2026-03-09 16:00:00",
                "total_personas": 200,
            },
            "input_summary": {
                "category": "儿童口腔护理",
                "price": 39.9,
                "core_claims": ["益生菌配方", "低氟防蛀", "孩子更愿意坚持刷牙"],
                "packaging_summary": "卡通水果视觉，突出年龄段和防蛀卖点。",
                "target_channels": ["天猫", "京东"],
                "competitive_anchors": ["欧乐B儿童牙膏"],
                "context_notes": "用于正式调研前预验证。",
                "missing_fields": ["目标人群", "竞品细节"],
            },
            "executive_summary": {
                "headline": "该概念在高线人群中有初步吸引力，但仍需强化价值证明。",
                "recommendation": "revise_then_retest",
                "business_recommendation": "建议优化后再进行下一轮测试",
                "avg_intention": 0.46,
                "key_risk": "价值感不够集中",
                "confidence_level": "中高",
                "confidence_reason": "价格、渠道和包装信息完整，但竞品锚点仍较少。",
            },
            "purchase_intent": {
                "average_score": 5.2,
                "average_intention": 0.46,
                "estimated_conversion_rate": 22.5,
                "decision_distribution": {"考虑购买": 80, "明确拒绝": 70, "犹豫观望": 50},
            },
            "segment_opportunity": {
                "top_segments": [{"segment": "高线忙碌派", "avg_intention": 0.61, "why_high_or_low": "认可专业感和效率表达。", "top_reason_tag": "专业背书"}],
                "weak_segments": [{"segment": "佛系粗养家", "avg_intention": 0.18, "why_high_or_low": "对高价和复杂卖点不敏感。", "top_reason_tag": "价值感不足"}],
                "full_table": [],
            },
            "reasons_to_buy": ["低氟防蛀", "益生菌配方"],
            "barriers": {"top_barriers": ["价值感不够集中"], "price_concern_share": 0.32},
            "diagnosis": {
                "decision_drivers": ["卖点较多，主价值记忆点不够集中。", "专业信任表达还不够强。", "包装首屏利益传达不够直给。"],
                "value_proposition_conflicts": ["儿童场景下，功能复合表达和安全感表达存在轻微张力。"],
                "competitive_limitations": ["本次已提供竞品锚点，但相对优势验证仍较浅。"],
            },
            "voice_of_consumer": {
                "supporters": [{"agent_name": "张三", "segment": "高线忙碌派", "stance_label": "支持者", "reason_tag": "专业背书", "quote": "这个卖点比较清晰，我愿意进一步了解。"}],
                "hesitant": [{"agent_name": "李四", "segment": "品质精算派", "stance_label": "犹豫者", "reason_tag": "证明不足", "quote": "我还想看更多证明，再决定。"}],
                "rejecting": [{"agent_name": "王五", "segment": "佛系粗养家", "stance_label": "拒绝者", "reason_tag": "价格敏感", "quote": "价格没必要这么高，我不会优先买。"}],
            },
            "optimization_suggestions": ["强化核心价值表达", "压缩首屏信息层级"],
            "action_plan": {
                "immediate_actions": ["收敛成 1 个主卖点 + 2 个辅助卖点。"],
                "next_round_prerequisites": ["补充更直接的专业背书素材。"],
                "recommended_next_tests": ["比较“专业防蛀”与“趣味刷牙”两条主张。"],
            },
            "report_boundary": {
                "input_completeness": 0.86,
                "missing_fields": ["竞品细节"],
                "credibility_notes": ["当前结论可信度中高，但竞品优势判断仍有限。"],
            },
            "appendix": {"discussion": {"consensus_level": 0.71}, "deep_dive_interview_count": 6},
        }

        html = renderer_module.HTMLReportRenderer().render(sample_report)

        self.assertIn("一句话结论", html)
        self.assertIn("结论依据拆解", html)
        self.assertIn("核心指标概览", html)
        self.assertIn("人群接受度与原因解释", html)
        self.assertIn("价值主张诊断", html)
        self.assertIn("下一步动作建议", html)
        self.assertIn("说明与可信度边界", html)
        self.assertIn("建议优化后再进行下一轮测试", html)
        self.assertNotIn("revise_then_retest", html)


if __name__ == "__main__":
    unittest.main()
