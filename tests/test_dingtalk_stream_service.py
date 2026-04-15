import importlib.util
import tempfile
import time
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

    def test_preflight_rejects_known_bad_python_runtime_combo(self):
        module = self.load_or_fail()

        warning = module.validate_runtime_environment(
            python_version="3.14.0",
            dingtalk_stream_version="0.24.3",
            websockets_version="16.0",
        )

        self.assertIn("unsupported", warning.lower())

    def test_start_forever_raises_clear_error_when_required_credentials_are_missing(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            session_manager = None

        service = module.DingTalkStreamBotService(
            workflow=FakeWorkflow(),
            config=module.DingTalkStreamConfig(app_key="", app_secret=""),
        )

        class StubClient:
            def __init__(self):
                self.called = False

            def start_forever(self):
                self.called = True

        stub_client = StubClient()
        service.client = stub_client

        with self.assertRaises(RuntimeError) as context:
            service.start_forever()

        self.assertIn("missing", str(context.exception).lower())
        self.assertFalse(stub_client.called)

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
                    "text": {"content": "@机器人 我想做妈妈定性研究"},
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
        self.assertIn("妈妈定性研究", workflow.events[0]["text"])
        self.assertEqual(handler.sent_text, ["研究任务信息清单"])

    def test_process_sends_clarification_message_for_blocked_request(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.task_ids = []

            def handle_message(self, event):
                return {
                    "status": "awaiting_clarification",
                    "task_id": None,
                    "messages": [{"type": "text", "content": "请补充产品信息或核心卖点。"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                self.task_ids.append(task_id)
                raise AssertionError("run_pending_task should not be called")

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
                    "text": {"content": "按当前信息运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(handler.sent_text, ["请补充产品信息或核心卖点。"])
        self.assertEqual(handler.sent_markdown, [])
        self.assertEqual(workflow.task_ids, [])

    def test_handler_runs_pending_task_and_sends_qualitative_markdown_report(self):
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
                    "messages": [{"type": "text", "content": "简版结论：妈妈会先验证可信度，再考虑购买。"}],
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
                    "text": {"content": "按当前信息运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(workflow.task_ids, ["task-123"])
        self.assertEqual(handler.sent_text, ["开始生成妈妈原声与研究总结"])
        self.assertEqual(len(handler.sent_markdown), 1)
        self.assertIn("简版结论：妈妈会先验证可信度", handler.sent_markdown[0][1])
        self.assertIn("https://bot.example.com/reports/task-123.html", handler.sent_markdown[0][1])

    def test_handler_sends_incomplete_result_text_when_pending_task_errors(self):
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
                    "text": {"content": "按当前信息运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(workflow.task_ids, ["task-123"])
        self.assertEqual(
            handler.sent_text,
            ["开始生成妈妈原声与研究总结", "本次结果不完整，请稍后重试"],
        )
        self.assertEqual(handler.sent_markdown, [])

    def test_handler_batches_messages_inside_aggregation_window(self):
        module = self.load_or_fail()

        class FakeWorkflow:
            def __init__(self):
                self.events = []
                self.session_manager = type(
                    "SessionManager",
                    (),
                    {"find_session_for": staticmethod(lambda group_id, conversation_id, user_id: None)},
                )()

            def handle_message(self, event):
                self.events.append(event)
                return {
                    "status": "collecting",
                    "task_id": None,
                    "messages": [{"type": "text", "content": "ok"}],
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

        def callback(message_id: str, text: str):
            return type(
                "CallbackMessage",
                (),
                {
                    "data": {
                        "conversationId": "conv-agg",
                        "senderStaffId": "user-agg",
                        "senderId": "sender-agg",
                        "senderCorpId": "corp-agg",
                        "msgtype": "text",
                        "text": {"content": text},
                        "sessionWebhook": "https://example.com/webhook",
                        "isInAtList": True,
                        "conversationType": "2",
                        "messageId": message_id,
                        "createAt": int(time.time() * 1000),
                    }
                },
            )()

        workflow = FakeWorkflow()
        config = module.DingTalkStreamConfig(
            app_key="k",
            app_secret="s",
            aggregation_window_seconds=0.05,
        )
        handler = RecordingHandler(workflow, config)

        handler.process(callback("msg-1", "产品信息：儿童牙膏"))
        handler.process(callback("msg-2", "用户问题：会不会买"))
        time.sleep(0.12)

        self.assertEqual(len(workflow.events), 1)
        self.assertIn("儿童牙膏", workflow.events[0]["text"])
        self.assertIn("会不会买", workflow.events[0]["text"])

    def test_handler_reoffers_suspended_messages_after_completion(self):
        module = self.load_or_fail()

        class SessionManager:
            def __init__(self):
                self.session = type(
                    "Session",
                    (),
                    {
                        "session_id": "session-1",
                        "status": "completed",
                        "user_id": "user-1",
                        "suspended_messages": [],
                    },
                )()

            def find_session_for(self, group_id, conversation_id, user_id):
                return self.session

            def save(self, session):
                self.session = session

        class FakeWorkflow:
            def __init__(self):
                self.session_manager = SessionManager()

            def handle_message(self, event):
                return {
                    "status": "running",
                    "task_id": "task-123",
                    "messages": [{"type": "text", "content": "running"}],
                    "html_report_path": None,
                    "json_report_path": None,
                }

            def run_pending_task(self, task_id):
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "messages": [{"type": "text", "content": "done"}],
                    "html_report_path": "C:/reports/task-123.html",
                    "json_report_path": "C:/reports/task-123.json",
                    "public_report_url": "",
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
        config = module.DingTalkStreamConfig(app_key="k", app_secret="s", aggregation_window_seconds=0.0)
        handler = RecordingHandler(workflow, config)
        handler.suspend_queue.enqueue("session-1", "请顺便考虑成人洗发水的补充问题")

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
                    "text": {"content": "按当前信息运行"},
                    "sessionWebhook": "https://example.com/webhook",
                    "isInAtList": True,
                    "conversationType": "2",
                    "messageId": "msg-123",
                }
            },
        )()

        handler.process(callback_message)

        self.assertEqual(workflow.session_manager.session.suspended_messages, ["请顺便考虑成人洗发水的补充问题"])
        self.assertTrue(any("补充消息" in text for text in handler.sent_text))


if __name__ == "__main__":
    unittest.main()
