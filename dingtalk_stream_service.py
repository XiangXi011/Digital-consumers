import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import requests
from dingtalk_stream import AsyncChatbotHandler, ChatbotMessage, Credential, DingTalkStreamClient


def _load_workspace_dotenv(base_dir: Path) -> dict[str, str]:
    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_config_value(name: str, dotenv_values: dict[str, str], default: str = "") -> str:
    if name in os.environ:
        return os.environ[name]
    if name in dotenv_values:
        return dotenv_values[name]
    return default


@dataclass
class DingTalkStreamConfig:
    app_key: str = ""
    app_secret: str = ""
    report_public_base_url: str = ""
    image_dir: str = "outputs/dingtalk_incoming_images"
    max_workers: int = 4

    @classmethod
    def from_env(cls, base_dir: Path | None = None):
        dotenv_values = _load_workspace_dotenv(base_dir or Path.cwd())
        max_workers_raw = _get_config_value("DINGTALK_STREAM_MAX_WORKERS", dotenv_values, "4")
        try:
            max_workers = int(max_workers_raw)
        except ValueError:
            max_workers = 4

        return cls(
            app_key=_get_config_value("DINGTALK_APP_KEY", dotenv_values, ""),
            app_secret=_get_config_value("DINGTALK_APP_SECRET", dotenv_values, ""),
            report_public_base_url=_get_config_value("DINGTALK_REPORT_PUBLIC_BASE_URL", dotenv_values, "").rstrip("/"),
            image_dir=_get_config_value("DINGTALK_IMAGE_DIR", dotenv_values, "outputs/dingtalk_incoming_images"),
            max_workers=max_workers,
        )


class DingTalkLangGraphHandler(AsyncChatbotHandler):
    def __init__(self, workflow, config: DingTalkStreamConfig):
        super().__init__(max_workers=config.max_workers)
        self.workflow = workflow
        self.config = config
        self.image_dir = Path(config.image_dir)
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def process(self, callback_message):
        incoming_message = ChatbotMessage.from_dict(callback_message.data)
        if not self._should_process(incoming_message):
            return

        event = self._build_workflow_event(incoming_message)
        result = self.workflow.handle_message(event)

        if result.get("status") == "running" and result.get("task_id"):
            finished = self.workflow.run_pending_task(result["task_id"])
            if finished.get("status") == "completed":
                self._send_completion_message(finished, incoming_message)
            else:
                self._send_workflow_messages(finished, incoming_message)
            return

        self._send_workflow_messages(result, incoming_message)

    def _should_process(self, incoming_message: ChatbotMessage) -> bool:
        if incoming_message.conversation_type == "1":
            return True
        if incoming_message.is_in_at_list:
            return True

        session = self.workflow.session_manager.find_session_for(
            incoming_message.sender_corp_id or incoming_message.chatbot_corp_id or "dingtalk",
            incoming_message.conversation_id,
            incoming_message.sender_staff_id or incoming_message.sender_id or "unknown-user",
        )
        return bool(session and session.user_id == (incoming_message.sender_staff_id or incoming_message.sender_id))

    def _build_workflow_event(self, incoming_message: ChatbotMessage) -> dict:
        text_parts = self.extract_text_from_incoming_message(incoming_message) or []
        text = "\n".join(part.strip() for part in text_parts if part and part.strip()).strip()
        attachments = self._extract_attachment_paths(incoming_message)
        return {
            "group_id": incoming_message.sender_corp_id or incoming_message.chatbot_corp_id or "dingtalk",
            "conversation_id": incoming_message.conversation_id,
            "user_id": incoming_message.sender_staff_id or incoming_message.sender_id or "unknown-user",
            "text": text,
            "attachments": attachments,
        }

    def _extract_attachment_paths(self, incoming_message: ChatbotMessage) -> List[str]:
        download_codes = incoming_message.get_image_list() or []
        saved_paths: List[str] = []
        for index, download_code in enumerate(download_codes, start=1):
            download_url = self.get_image_download_url(download_code)
            if not download_url:
                continue
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()

            suffix = ".png"
            content_type = response.headers.get("Content-Type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                suffix = ".jpg"

            filename = f"{incoming_message.conversation_id}_{incoming_message.message_id or 'message'}_{index}{suffix}"
            path = self.image_dir / filename
            path.write_bytes(response.content)
            saved_paths.append(str(path))
        return saved_paths

    def _send_workflow_messages(self, result: dict, incoming_message: ChatbotMessage):
        for message in result.get("messages", []):
            content = message.get("content", "")
            if content:
                self.reply_text(content, incoming_message)

    def _send_completion_message(self, result: dict, incoming_message: ChatbotMessage):
        messages = result.get("messages", [])
        summary = messages[0]["content"] if messages else "报告已生成。"
        report_url = result.get("public_report_url") or self._build_report_url(result.get("html_report_path"))

        markdown_lines = [summary]
        if report_url:
            markdown_lines.append("")
            markdown_lines.append(f"[查看HTML报告]({report_url})")
        elif result.get("html_report_path"):
            markdown_lines.append("")
            markdown_lines.append("HTML报告已生成，但当前未配置公网访问地址。")
            markdown_lines.append(f"本地报告路径：{result['html_report_path']}")

        self.reply_markdown(
            title="数字消费者洞察报告",
            text="\n".join(markdown_lines),
            incoming_message=incoming_message,
        )

    def _build_report_url(self, html_report_path: Optional[str]) -> str:
        if not html_report_path or not self.config.report_public_base_url:
            return ""
        filename = Path(html_report_path).name
        return urljoin(f"{self.config.report_public_base_url}/", filename)


class DingTalkStreamBotService:
    def __init__(self, workflow, config: DingTalkStreamConfig | None = None):
        self.workflow = workflow
        self.config = config or DingTalkStreamConfig.from_env()
        self.credential = Credential(self.config.app_key, self.config.app_secret)
        self.client = DingTalkStreamClient(self.credential)
        self.handler = DingTalkLangGraphHandler(workflow, self.config)
        self.client.register_callback_handler(ChatbotMessage.TOPIC, self.handler)
        self.client.register_callback_handler(ChatbotMessage.DELEGATE_TOPIC, self.handler)

    def start_forever(self):
        self.client.start_forever()
