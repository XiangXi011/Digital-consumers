import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DingTalkStreamServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "dingtalk_stream_service.py"

    def load_or_fail(self):
        if not self.module_path.exists():
            self.fail("dingtalk_stream_service.py is missing")
        return load_module("dingtalk_stream_service_under_test", self.module_path)

    def test_stream_config_can_load_workspace_dotenv(self):
        module = self.load_or_fail()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".env").write_text(
                "\n".join(
                    [
                        "DINGTALK_APP_KEY=test-app-key",
                        "DINGTALK_APP_SECRET=test-app-secret",
                        "DINGTALK_REPORT_PUBLIC_BASE_URL=https://bot.example.com/reports",
                        "DINGTALK_STREAM_MAX_WORKERS=6",
                    ]
                ),
                encoding="utf-8",
            )

            config = module.DingTalkStreamConfig.from_env(base_dir=temp_path)

        self.assertEqual(config.app_key, "test-app-key")
        self.assertEqual(config.app_secret, "test-app-secret")
        self.assertEqual(config.report_public_base_url, "https://bot.example.com/reports")
        self.assertEqual(config.max_workers, 6)

    def test_handler_converts_stream_message_into_workflow_event(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.events = []

            def handle_message(self, event):
                self.events.append(event)
                return {
                    "status": "collecting",
                    "task_id": None,
                    "messages": [{"type": "text", "content": "完整资料清单"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

        class RecordingHandler(module.DingTalkLangGraphHandler):
            def __init__(self, workflow, config):
                super().__init__(workflow, config)
                self.sent_text = []
                self.sent_markdown = []

            def reply_text(self, text, incoming_message):
                self.sent_text.append(text)
                return {"ok": True}

            def reply_markdown(self, title, text, incoming_message):
                self.sent_markdown.append((title, text))
                return {"ok": True}

            def _extract_attachment_paths(self, incoming_message):
                return []

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(app_key="k", app_secret="s")
        handler = RecordingHandler(workflow, config)
        callback_message = type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-1",
                    "senderId": "sender-1",
                    "senderCorpId": "corp-1",
                    "msgtype": "text",
                    "text": {"content": "@机器人 我要做新品测试"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(len(workflow.events), 1)
        self.assertEqual(workflow.events[0]["group_id"], "corp-1")
        self.assertEqual(workflow.events[0]["conversation_id"], "conv-1")
        self.assertEqual(workflow.events[0]["user_id"], "user-1")
        self.assertIn("新品测试", workflow.events[0]["text"])
        self.assertEqual(handler.sent_text, ["完整资料清单"])

    def test_handler_runs_pending_task_and_sends_markdown_report(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.task_ids = []

            def handle_message(self, event):
                return {
                    "status": "running",
                    "task_id": "task-123",
                    "messages": [{"type": "text", "content": "开始分析"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                self.task_ids.append(task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "messages": [{"type": "text", "content": "简版结论：建议继续优化"}],
                    "html_report_path": "C:/reports/task-123.html",
                    "json_report_path": "C:/reports/task-123.json",
                }

        class RecordingHandler(module.DingTalkLangGraphHandler):
            def __init__(self, workflow, config):
                super().__init__(workflow, config)
                self.sent_text = []
                self.sent_markdown = []

            def reply_text(self, text, incoming_message):
                self.sent_text.append(text)
                return {"ok": True}

            def reply_markdown(self, title, text, incoming_message):
                self.sent_markdown.append((title, text))
                return {"ok": True}

            def _extract_attachment_paths(self, incoming_message):
                return []

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(
            app_key="k",
            app_secret="s",
            report_public_base_url="https://bot.example.com/reports",
        )
        handler = RecordingHandler(workflow, config)
        callback_message = type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-1",
                    "senderId": "sender-1",
                    "senderCorpId": "corp-1",
                    "msgtype": "text",
                    "text": {"content": "按现有资料运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(workflow.task_ids, ["task-123"])
        self.assertEqual(handler.sent_text, ["开始分析"])
        self.assertEqual(len(handler.sent_markdown), 1)
        self.assertEqual(handler.sent_markdown[0][0], "数字消费者洞察报告")
        self.assertIn("简版结论：建议继续优化", handler.sent_markdown[0][1])
        self.assertIn("https://bot.example.com/reports/task-123.html", handler.sent_markdown[0][1])

    def test_handler_without_public_url_includes_local_report_path_hint(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def handle_message(self, event):
                return {
                    "status": "running",
                    "task_id": "task-123",
                    "messages": [{"type": "text", "content": "开始分析"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "messages": [{"type": "text", "content": "简版结论：建议继续优化"}],
                    "html_report_path": "C:/reports/task-123.html",
                    "json_report_path": "C:/reports/task-123.json",
                }

        class RecordingHandler(module.DingTalkLangGraphHandler):
            def __init__(self, workflow, config):
                super().__init__(workflow, config)
                self.sent_text = []
                self.sent_markdown = []

            def reply_text(self, text, incoming_message):
                self.sent_text.append(text)
                return {"ok": True}

            def reply_markdown(self, title, text, incoming_message):
                self.sent_markdown.append((title, text))
                return {"ok": True}

            def _extract_attachment_paths(self, incoming_message):
                return []

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(app_key="k", app_secret="s")
        handler = RecordingHandler(workflow, config)
        callback_message = type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-1",
                    "senderId": "sender-1",
                    "senderCorpId": "corp-1",
                    "msgtype": "text",
                    "text": {"content": "按现有资料运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(len(handler.sent_markdown), 1)
        self.assertIn("HTML报告已生成，但当前未配置公网访问地址。", handler.sent_markdown[0][1])
        self.assertIn("C:/reports/task-123.html", handler.sent_markdown[0][1])

    def test_handler_prefers_task_level_public_report_url(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def handle_message(self, event):
                return {
                    "status": "running",
                    "task_id": "task-123",
                    "messages": [{"type": "text", "content": "开始分析"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "messages": [{"type": "text", "content": "简版结论：建议继续优化"}],
                    "html_report_path": "C:/reports/task-123.html",
                    "json_report_path": "C:/reports/task-123.json",
                    "public_report_url": "https://dingtalk-reports.vercel.app/task-123.html",
                }

        class RecordingHandler(module.DingTalkLangGraphHandler):
            def __init__(self, workflow, config):
                super().__init__(workflow, config)
                self.sent_text = []
                self.sent_markdown = []

            def reply_text(self, text, incoming_message):
                self.sent_text.append(text)
                return {"ok": True}

            def reply_markdown(self, title, text, incoming_message):
                self.sent_markdown.append((title, text))
                return {"ok": True}

            def _extract_attachment_paths(self, incoming_message):
                return []

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(app_key="k", app_secret="s")
        handler = RecordingHandler(workflow, config)
        callback_message = type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-1",
                    "senderId": "sender-1",
                    "senderCorpId": "corp-1",
                    "msgtype": "text",
                    "text": {"content": "按现有资料运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(len(handler.sent_markdown), 1)
        self.assertIn("https://dingtalk-reports.vercel.app/task-123.html", handler.sent_markdown[0][1])

    def test_handler_accepts_non_at_image_follow_up_when_session_exists(self):
        module = self.load_or_fail()

        class FakeSessionManager:
            def find_session_for(self, group_id, conversation_id, user_id):
                return type("Session", (), {"user_id": "user-1"})()

        class FakeWorkflow:
            def __init__(self):
                self.events = []
                self.session_manager = FakeSessionManager()

            def handle_message(self, event):
                self.events.append(event)
                return {
                    "status": "awaiting_run_confirmation",
                    "task_id": None,
                    "messages": [{"type": "text", "content": "已收到图片"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

        class RecordingHandler(module.DingTalkLangGraphHandler):
            def __init__(self, workflow, config):
                super().__init__(workflow, config)
                self.sent_text = []

            def reply_text(self, text, incoming_message):
                self.sent_text.append(text)
                return {"ok": True}

            def _extract_attachment_paths(self, incoming_message):
                return ["C:/tmp/packaging.png"]

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(app_key="k", app_secret="s")
        handler = RecordingHandler(workflow, config)
        callback_message = type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-1",
                    "senderId": "sender-1",
                    "senderCorpId": "corp-1",
                    "msgtype": "picture",
                    "content": {"downloadCode": "d1", "pictureDownloadCode": "p1"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": False,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(len(workflow.events), 1)
        self.assertEqual(workflow.events[0]["attachments"], ["C:/tmp/packaging.png"])
        self.assertEqual(handler.sent_text, ["已收到图片"])

    def test_group_message_without_at_only_continues_current_users_session(self):
        module = self.load_or_fail()

        class FakeSessionManager:
            def find_session_for(self, group_id, conversation_id, user_id):
                if user_id == "user-2":
                    return type("Session", (), {"user_id": "user-2"})()
                return None

        class FakeWorkflow:
            def __init__(self):
                self.events = []
                self.session_manager = FakeSessionManager()

            def handle_message(self, event):
                self.events.append(event)
                return {
                    "status": "awaiting_run_confirmation",
                    "task_id": None,
                    "messages": [{"type": "text", "content": "已续接当前任务"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

        class RecordingHandler(module.DingTalkLangGraphHandler):
            def __init__(self, workflow, config):
                super().__init__(workflow, config)
                self.sent_text = []

            def reply_text(self, text, incoming_message):
                self.sent_text.append(text)
                return {"ok": True}

            def _extract_attachment_paths(self, incoming_message):
                return []

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(app_key="k", app_secret="s")
        handler = RecordingHandler(workflow, config)
        callback_message = type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-2",
                    "senderId": "sender-2",
                    "senderCorpId": "corp-1",
                    "msgtype": "text",
                    "text": {"content": "补充一句渠道京东"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": False,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(len(workflow.events), 1)
        self.assertEqual(workflow.events[0]["user_id"], "user-2")
        self.assertEqual(handler.sent_text, ["已续接当前任务"])


if __name__ == "__main__":
    unittest.main()
