import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import requests
from dingtalk_stream import AsyncChatbotHandler, ChatbotMessage, Credential, DingTalkStreamClient


logger = logging.getLogger(__name__)

from backend.infra.privacy_utils import matches_hashed_identifier
from backend.infra.redis_infra import (
    AggregationWindow,
    EventDeduplicator,
    InMemoryStore,
    OrderingGuard,
    SuspendQueue,
)


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


def _parse_version_tuple(version_text: str) -> tuple[int, ...]:
    values = []
    for part in version_text.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        values.append(int(digits))
    return tuple(values)


def _safe_package_version(package_name: str) -> str:
    try:
        return metadata.version(package_name)
    except Exception as exc:
        logger.debug("Failed to get version for package %s: %s", package_name, exc)
        return "unknown"


def validate_runtime_environment(
    python_version: str | None = None,
    dingtalk_stream_version: str | None = None,
    websockets_version: str | None = None,
) -> str:
    python_version = python_version or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    dingtalk_stream_version = dingtalk_stream_version or _safe_package_version("dingtalk-stream")
    websockets_version = websockets_version or _safe_package_version("websockets")
    python_tuple = _parse_version_tuple(python_version)
    dingtalk_tuple = _parse_version_tuple(dingtalk_stream_version)
    websockets_tuple = _parse_version_tuple(websockets_version)

    if python_tuple >= (3, 15):
        return (
            "Unsupported DingTalk stream runtime: Python 3.15+ is not approved for the "
            f"current dingtalk-stream/websockets stack ({dingtalk_stream_version} / {websockets_version})."
        )

    if python_tuple >= (3, 14) and (
        dingtalk_tuple <= (0, 24, 3) or websockets_tuple >= (16, 0)
    ):
        return (
            "Unsupported DingTalk stream runtime: Python 3.14 is not approved for the "
            f"current dingtalk-stream/websockets stack ({dingtalk_stream_version} / {websockets_version})."
        )

    return ""


@dataclass
class DingTalkStreamConfig:
    app_key: str = ""
    app_secret: str = ""
    report_public_base_url: str = ""
    image_dir: str = "outputs/dingtalk_incoming_images"
    max_workers: int = 4
    aggregation_window_seconds: float = 0.0

    @classmethod
    def from_env(cls, base_dir: Path | None = None):
        dotenv_values = _load_workspace_dotenv(base_dir or Path.cwd())
        max_workers_raw = _get_config_value("DINGTALK_STREAM_MAX_WORKERS", dotenv_values, "4")
        aggregation_window_raw = _get_config_value(
            "DINGTALK_AGGREGATION_WINDOW_SECONDS",
            dotenv_values,
            "3.0",
        )
        try:
            max_workers = int(max_workers_raw)
        except ValueError:
            max_workers = 4
        try:
            aggregation_window_seconds = float(aggregation_window_raw)
        except ValueError:
            aggregation_window_seconds = 3.0

        return cls(
            app_key=_get_config_value("DINGTALK_APP_KEY", dotenv_values, ""),
            app_secret=_get_config_value("DINGTALK_APP_SECRET", dotenv_values, ""),
            report_public_base_url=_get_config_value("DINGTALK_REPORT_PUBLIC_BASE_URL", dotenv_values, "").rstrip("/"),
            image_dir=_get_config_value("DINGTALK_IMAGE_DIR", dotenv_values, "outputs/dingtalk_incoming_images"),
            max_workers=max_workers,
            aggregation_window_seconds=aggregation_window_seconds,
        )


class DingTalkLangGraphHandler(AsyncChatbotHandler):
    def __init__(self, workflow, config: DingTalkStreamConfig, runtime_store=None):
        super().__init__(max_workers=config.max_workers)
        self.workflow = workflow
        self.config = config
        self.image_dir = Path(config.image_dir)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_store = runtime_store or InMemoryStore()
        self.event_deduplicator = EventDeduplicator(self.runtime_store)
        self.ordering_guard = OrderingGuard(self.runtime_store)
        self.aggregation_window = AggregationWindow(
            self.runtime_store,
            window_seconds=config.aggregation_window_seconds or 0.0,
        )
        self.suspend_queue = SuspendQueue(self.runtime_store)
        self._aggregation_lock = threading.Lock()
        self._aggregation_buffers: dict[str, dict] = {}
        self._aggregation_timers: dict[str, threading.Timer] = {}

    def process(self, callback_message):
        incoming_message = ChatbotMessage.from_dict(callback_message.data)
        logger.info("Received message: type=%s, conversation_type=%s, is_at=%s, sender=%s",
                    getattr(incoming_message, 'msgtype', 'unknown'),
                    incoming_message.conversation_type,
                    incoming_message.is_in_at_list,
                    incoming_message.sender_staff_id or incoming_message.sender_id)
        
        if not self._should_process(incoming_message):
            logger.info("Message filtered out by _should_process")
            return

        event = self._build_workflow_event(incoming_message)
        logger.info("Processing event: text=%s", event.get('text', '')[:100])
        
        if not self._apply_runtime_guards(event):
            logger.info("Event blocked by runtime guards")
            return

        if self._is_dispatching_session(event):
            self._process_event(event, incoming_message)
            return

        if self.config.aggregation_window_seconds > 0:
            self._buffer_or_process(event, incoming_message)
            return

        self._process_event(event, incoming_message)

    def _is_dispatching_session(self, event: dict) -> bool:
        if not getattr(self.workflow, "session_manager", None):
            return False
        session = self.workflow.session_manager.find_session_for(
            event["group_id"],
            event["conversation_id"],
            event["user_id"],
        )
        return bool(session is not None and getattr(session, "status", "") in {"running", "dispatching"})

    def _process_event(self, event: dict, incoming_message: ChatbotMessage):
        session = None
        if getattr(self.workflow, "session_manager", None):
            session = self.workflow.session_manager.find_session_for(
                event["group_id"],
                event["conversation_id"],
                event["user_id"],
            )
        if session is not None and getattr(session, "status", "") in {"running", "dispatching"}:
            import json as _json
            suspended_entry = _json.dumps({
                "text": event.get("text", ""),
                "user_id": event.get("user_id", ""),
                "create_ts": event.get("create_ts", 0),
                "attachments": event.get("attachments", []),
            }, ensure_ascii=False)
            self.suspend_queue.enqueue(session.session_id, suspended_entry)
            self.reply_text("当前任务仍在运行，已暂存你的补充消息，完成后可继续处理。", incoming_message)
            return

        result = self.workflow.handle_message(event)
        self._send_workflow_messages(result, incoming_message)

        if result.get("status") == "running" and result.get("task_id"):
            finished = self.workflow.run_pending_task(result["task_id"])
            if finished.get("status") == "error":
                self._send_workflow_messages(finished, incoming_message)
            else:
                self._send_completion_message(finished, incoming_message)
                self._reoffer_suspended_messages(event, incoming_message)

    def _buffer_or_process(self, event: dict, incoming_message: ChatbotMessage):
        event_key = self._event_key(event)
        # Use local arrival time for the sliding aggregation window so closely
        # spaced messages are batched even if upstream timestamps jitter.
        timestamp_seconds = time.monotonic()

        with self._aggregation_lock:
            pending = self._aggregation_buffers.get(event_key)
            if pending is None:
                self.aggregation_window.should_aggregate(event_key, timestamp_seconds or 0.0)
                self._aggregation_buffers[event_key] = {
                    "event": dict(event),
                    "incoming_message": incoming_message,
                }
                timer = threading.Timer(
                    self.config.aggregation_window_seconds,
                    self._flush_aggregated_event,
                    args=(event_key,),
                )
                timer.daemon = True
                self._aggregation_timers[event_key] = timer
                timer.start()
                return

            if self.aggregation_window.should_aggregate(event_key, timestamp_seconds or 0.0):
                pending["event"] = self._aggregate_event(pending["event"], event)
                pending["incoming_message"] = incoming_message
                return

            flushed = self._aggregation_buffers.pop(event_key)
            timer = self._aggregation_timers.pop(event_key, None)
            if timer is not None:
                timer.cancel()

        # NOTE: Lock is released before processing to avoid blocking other event keys.
        # This may cause slight ordering issues if _process_event is slow, but is
        # acceptable for the DingTalk use case where message latency is tolerable.
        self._process_event(flushed["event"], flushed["incoming_message"])
        self._buffer_or_process(event, incoming_message)

    def _flush_aggregated_event(self, event_key: str):
        with self._aggregation_lock:
            pending = self._aggregation_buffers.pop(event_key, None)
            self._aggregation_timers.pop(event_key, None)
        if not pending:
            return
        self._process_event(pending["event"], pending["incoming_message"])

    def _reoffer_suspended_messages(self, event: dict, incoming_message: ChatbotMessage):
        if not getattr(self.workflow, "session_manager", None):
            return
        session = self.workflow.session_manager.find_session_for(
            event["group_id"],
            event["conversation_id"],
            event["user_id"],
        )
        if session is None or not getattr(session, "session_id", ""):
            return
        if not self.suspend_queue.has_pending(session.session_id):
            return

        drained_messages = self.suspend_queue.drain(session.session_id)
        if not drained_messages:
            return

        existing = list(getattr(session, "suspended_messages", []) or [])
        for raw_entry in drained_messages:
            # Parse structured suspend entry; fall back to raw text for backwards compat
            try:
                import json
                entry = json.loads(raw_entry)
                message_text = entry.get("text", raw_entry)
            except (json.JSONDecodeError, TypeError):
                message_text = raw_entry
            if message_text not in existing:
                existing.append(message_text)
        session.suspended_messages = existing
        if hasattr(self.workflow.session_manager, "save"):
            self.workflow.session_manager.save(session)

        self.reply_text(
            f"我还收到了 {len(drained_messages)} 条补充消息，已为你暂存。如需继续，请直接回复并带上这些补充消息重新评估。",
            incoming_message,
        )

    def _event_key(self, event: dict) -> str:
        return "__".join(
            [
                str(event.get("group_id", "")),
                str(event.get("conversation_id", "")),
                str(event.get("user_id", "")),
            ]
        )

    def _aggregate_event(self, existing_event: dict, new_event: dict) -> dict:
        combined = dict(existing_event)
        existing_attachments = list(existing_event.get("attachments", []))
        combined["text"] = "\n".join(
            part
            for part in [str(existing_event.get("text", "")).strip(), str(new_event.get("text", "")).strip()]
            if part
        )
        combined["attachments"] = existing_attachments + [
            item for item in new_event.get("attachments", []) if item not in existing_attachments
        ]
        combined["create_ts"] = max(
            float(existing_event.get("create_ts") or 0),
            float(new_event.get("create_ts") or 0),
        )
        combined["msg_id"] = new_event.get("msg_id") or existing_event.get("msg_id")
        return combined

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
        return bool(
            session
            and matches_hashed_identifier(
                session.user_id,
                incoming_message.sender_staff_id or incoming_message.sender_id,
            )
        )

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
            "is_bot_mentioned": bool(incoming_message.is_in_at_list),
            "is_private_chat": incoming_message.conversation_type == "1",
            "create_ts": incoming_message.create_at,
            "msg_id": incoming_message.message_id or "",
            "event_type": getattr(incoming_message, "msgtype", "") or "message",
        }

    def _apply_runtime_guards(self, event: dict) -> bool:
        msg_id = str(event.get("msg_id") or "").strip()
        if msg_id and self.event_deduplicator.is_duplicate(msg_id):
            return False

        session_id = "__".join(
            [
                str(event.get("group_id", "")),
                str(event.get("conversation_id", "")),
                str(event.get("user_id", "")),
            ]
        )
        create_ts = float(event.get("create_ts") or 0)
        if create_ts and self.ordering_guard.is_stale(session_id, create_ts):
            return False

        return True

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
        if not self.config.app_key or not self.config.app_secret:
            raise RuntimeError("Missing DingTalk credentials: app_key/app_secret.")

        runtime_warning = validate_runtime_environment()
        if runtime_warning:
            raise RuntimeError(runtime_warning)

        self.client.start_forever()
