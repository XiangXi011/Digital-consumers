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

    def build_callback_message(self, text: str):
        return type(
            "CallbackMessage",
            (),
            {
                "data": {
                    "conversationId": "conv-1",
                    "senderStaffId": "user-1",
                    "senderId": "sender-1",
                    "senderCorpId": "corp-1",
                    "msgtype": "text",
                    "text": {"content": text},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

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

    def test_handler_converts_stream_message_into_research_event(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.events = []

            def handle_message(self, event):
                self.events.append(event)
                return {
                    "status": "collecting",
                    "task_id": None,
                    "messages": [{"type": "text", "content": "研究任务信息清单"}],
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

        handler.process(self.build_callback_message("@机器人 我想做妈妈定性研究"))

        self.assertEqual(len(workflow.events), 1)
        self.assertEqual(workflow.events[0]["group_id"], "corp-1")
        self.assertEqual(workflow.events[0]["conversation_id"], "conv-1")
        self.assertEqual(workflow.events[0]["user_id"], "user-1")
        self.assertIn("妈妈定性研究", workflow.events[0]["text"])
        self.assertEqual(handler.sent_text, ["研究任务信息清单"])
        self.assertEqual(handler.sent_markdown, [])

    def test_handler_runs_pending_task_and_sends_only_final_markdown_report(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.task_ids = []

            def handle_message(self, event):
                return {
                    "status": "running",
                    "task_id": "task-123",
                    "messages": [{"type": "text", "content": "开始生成妈妈原声与研究总结"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                self.task_ids.append(task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "messages": [{"type": "text", "content": "简版结论：多数妈妈先看可信度"}],
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

        handler.process(self.build_callback_message("按当前信息运行"))

        self.assertEqual(workflow.task_ids, ["task-123"])
        self.assertEqual(handler.sent_text, [])
        self.assertEqual(len(handler.sent_markdown), 1)
        self.assertEqual(handler.sent_markdown[0][0], "数字消费者洞察报告")
        self.assertIn("简版结论：多数妈妈先看可信度", handler.sent_markdown[0][1])
        self.assertIn("https://bot.example.com/reports/task-123.html", handler.sent_markdown[0][1])

    def test_handler_incomplete_run_sends_only_error_text(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.task_ids = []

            def handle_message(self, event):
                return {
                    "status": "running",
                    "task_id": "task-123",
                    "messages": [{"type": "text", "content": "开始生成妈妈原声与研究总结"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                self.task_ids.append(task_id)
                return {
                    "status": "error",
                    "task_id": task_id,
                    "messages": [{"type": "text", "content": "本次结果不完整，请稍后重试"}],
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

        handler.process(self.build_callback_message("按当前信息运行"))

        self.assertEqual(workflow.task_ids, ["task-123"])
        self.assertEqual(handler.sent_text, ["本次结果不完整，请稍后重试"])
        self.assertEqual(handler.sent_markdown, [])


if __name__ == "__main__":
    unittest.main()
