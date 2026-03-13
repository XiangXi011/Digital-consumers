import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


FIELD_SPECS = [
    {"key": "mode", "label": "模式", "priority": "P0"},
    {"key": "question_type", "label": "研究问题", "priority": "P0"},
    {"key": "persona_id", "label": "指定妈妈画像", "priority": "P0"},
    {"key": "user_question", "label": "用户问题", "priority": "P0"},
    {"key": "background_material", "label": "背景资料", "priority": "P1"},
    {"key": "product_info", "label": "产品信息", "priority": "P1"},
    {"key": "copy_material", "label": "文案或卖点", "priority": "P1"},
]

FIELD_LABEL_MAP = {
    "模式": "mode",
    "研究问题": "question_type",
    "指定妈妈画像": "persona_id",
    "妈妈画像": "persona_id",
    "画像": "persona_id",
    "用户问题": "user_question",
    "问题": "user_question",
    "背景资料": "background_material",
    "背景": "background_material",
    "产品信息": "product_info",
    "产品": "product_info",
    "文案或卖点": "copy_material",
    "文案": "copy_material",
    "卖点": "copy_material",
}

MODE_ALIASES = {
    "多人模式": "multi",
    "多人": "multi",
    "8类妈妈": "multi",
    "八类妈妈": "multi",
    "单人模式": "single",
    "单人": "single",
}

QUESTION_TYPE_ALIASES = {
    "产品概念": "product_concept",
    "购买决策": "purchase_decision",
    "需求痛点": "needs_pain_points",
    "文案和卖点反馈": "copy_feedback",
    "文案反馈": "copy_feedback",
    "卖点反馈": "copy_feedback",
}

RUN_CONFIRM_TOKENS = ["按当前信息运行", "开始分析", "运行", "开始跑", "开始研究"]
WEAK_AFFIRM_TOKENS = ["好", "可以", "嗯", "好的", "行", "ok", "OK"]
DENIAL_TOKENS = ["等等", "先别", "不要", "暂停", "停", "别跑", "取消"]
AUTHORIZATION_WINDOW_SECONDS = 300  # 5 minutes
RESET_COMMAND_TOKENS = ["新任务", "重置任务", "清空任务", "重新开始"]
QUESTION_HINTS = ["?", "？", "会不会", "有没有", "为什么", "什么", "顾虑", "痛点", "文案", "卖点", "吸引力"]
FIELD_ALIASES = sorted(FIELD_LABEL_MAP.items(), key=lambda item: len(item[0]), reverse=True)
FIELD_ALIAS_PATTERN = re.compile("|".join(re.escape(alias) for alias, _ in FIELD_ALIASES))
FIELD_PREFIX_BOUNDARIES = set(" \t,，:：;；。!?？！[]【】()（）")
FIELD_VALUE_PREFIX_CHARS = " ：:;；，, \t"


def build_empty_fields() -> Dict[str, Dict[str, Any]]:
    return {
        spec["key"]: {
            "label": spec["label"],
            "priority": spec["priority"],
            "status": "missing",
            "value": None,
        }
        for spec in FIELD_SPECS
    }


def normalize_fields(raw_fields: Any) -> tuple[Dict[str, Dict[str, Any]], bool]:
    normalized = build_empty_fields()
    if not isinstance(raw_fields, dict):
        return normalized, False

    recognized_keys = set()
    for spec in FIELD_SPECS:
        key = spec["key"]
        raw_state = raw_fields.get(key)
        if not isinstance(raw_state, dict):
            continue
        recognized_keys.add(key)
        normalized[key] = {
            "label": raw_state.get("label", spec["label"]),
            "priority": raw_state.get("priority", spec["priority"]),
            "status": raw_state.get("status", "missing"),
            "value": raw_state.get("value"),
        }

    legacy_schema_detected = bool(raw_fields) and not recognized_keys
    return normalized, legacy_schema_detected


@dataclass
class TaskSession:
    session_id: str
    group_id: str
    conversation_id: str
    user_id: str
    status: str = "collecting"
    checklist_sent: bool = False
    partial_run_authorized: bool = False
    fields: Dict[str, Dict[str, Any]] = field(default_factory=build_empty_fields)
    missing_fields: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    follow_up_context: str = ""
    last_task_id: Optional[str] = None
    html_report_path: Optional[str] = None
    json_report_path: Optional[str] = None
    research_plan: Optional[Dict[str, Any]] = None
    authorization_requested_at: Optional[float] = None
    authorization_requested_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        fields, legacy_schema_detected = normalize_fields(data.get("fields"))
        if legacy_schema_detected:
            return cls(
                session_id=data["session_id"],
                group_id=data["group_id"],
                conversation_id=data["conversation_id"],
                user_id=data["user_id"],
                fields=fields,
                attachments=data.get("attachments", []),
            )
        return cls(
            session_id=data["session_id"],
            group_id=data["group_id"],
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            status=data.get("status", "collecting"),
            checklist_sent=data.get("checklist_sent", False),
            partial_run_authorized=data.get("partial_run_authorized", False),
            fields=fields,
            missing_fields=data.get("missing_fields", []),
            attachments=data.get("attachments", []),
            follow_up_context=data.get("follow_up_context", ""),
            last_task_id=data.get("last_task_id"),
            html_report_path=data.get("html_report_path"),
            json_report_path=data.get("json_report_path"),
            research_plan=data.get("research_plan"),
            authorization_requested_at=data.get("authorization_requested_at"),
            authorization_requested_by=data.get("authorization_requested_by"),
        )


class TaskSessionManager:
    def __init__(self, session_dir: Path | str, persona_path: Path | str, ai_client: Any | None = None):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.ai_client = ai_client
        self.persona_alias_map = self._load_persona_alias_map(Path(persona_path))

    def has_session_for(self, group_id: str, conversation_id: str, user_id: str) -> bool:
        return self._path_for(self._build_session_id(group_id, conversation_id, user_id)).exists()

    def find_session_for(self, group_id: str, conversation_id: str, user_id: str) -> Optional[TaskSession]:
        path = self._path_for(self._build_session_id(group_id, conversation_id, user_id))
        if not path.exists():
            return None
        return TaskSession.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def get_or_create(self, group_id: str, conversation_id: str, user_id: str) -> TaskSession:
        session_id = self._build_session_id(group_id, conversation_id, user_id)
        path = self._path_for(session_id)
        if path.exists():
            return self.load(session_id)
        session = TaskSession(
            session_id=session_id,
            group_id=group_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self.save(session)
        return session

    def reset_session(self, group_id: str, conversation_id: str, user_id: str) -> TaskSession:
        session_id = self._build_session_id(group_id, conversation_id, user_id)
        path = self._path_for(session_id)
        if path.exists():
            path.unlink()
        session = TaskSession(
            session_id=session_id,
            group_id=group_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self.save(session)
        return session

    def load(self, session_id: str) -> TaskSession:
        return TaskSession.from_dict(
            json.loads(self._path_for(session_id).read_text(encoding="utf-8"))
        )

    def save(self, session: TaskSession):
        session.missing_fields = self.get_missing_fields(session)
        self._path_for(session.session_id).write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_from_message(self, session: TaskSession, text: str, attachments: Optional[List[str]] = None):
        normalized_text = (text or "").strip()
        for attachment in attachments or []:
            if attachment not in session.attachments:
                session.attachments.append(attachment)

        for key, value in self._extract_field_updates(normalized_text):
            self._set_field_value(session, key, value)

        self._apply_inference(session, normalized_text)
        self.save(session)

    def has_run_confirmation(self, text: str) -> bool:
        normalized = (text or "").strip()
        lowered = normalized.lower()
        return any(token in normalized for token in RUN_CONFIRM_TOKENS) or lowered == "run"

    def classify_authorization(
        self, text: str, user_id: str, event: dict, session: Optional["TaskSession"] = None,
    ) -> str:
        """Classify authorization intent with user_id binding and time-window checks.

        Returns one of: "strong_affirm", "weak_affirm", "denial", "none".
        """
        import time

        normalized = (text or "").strip()
        lowered = normalized.lower()
        is_direct = event.get("is_bot_mentioned", False) or event.get("is_private_chat", False)

        # Check denial first
        if any(token in normalized for token in DENIAL_TOKENS):
            return "denial"

        # Strong affirmation: explicit run tokens + bot-mention/private chat
        has_run_token = any(token in normalized for token in RUN_CONFIRM_TOKENS) or lowered == "run"
        if has_run_token:
            if is_direct:
                return "strong_affirm"
            return "none"

        # Weak affirmation: short confirmation words
        if lowered in [t.lower() for t in WEAK_AFFIRM_TOKENS]:
            if not is_direct:
                return "none"
            if session is None or session.status != "awaiting_run_confirmation":
                return "none"
            if session.authorization_requested_by != user_id:
                return "none"
            if session.authorization_requested_at is None:
                return "none"
            now = event.get("create_ts")
            if now is None:
                now = time.time() * 1000  # fallback to current time in ms
            elapsed_seconds = (float(now) - session.authorization_requested_at) / 1000
            if elapsed_seconds > AUTHORIZATION_WINDOW_SECONDS:
                return "none"
            return "weak_affirm"

        return "none"

    def has_reset_command(self, text: str) -> bool:
        normalized = (text or "").strip()
        return any(token in normalized for token in RESET_COMMAND_TOKENS)

    def get_missing_fields(self, session: TaskSession) -> List[str]:
        missing = []
        required_keys = {"mode", "question_type", "user_question"}
        if session.fields["mode"]["value"] == "single":
            required_keys.add("persona_id")

        for spec in FIELD_SPECS:
            if spec["key"] not in required_keys:
                continue
            if session.fields[spec["key"]]["status"] == "missing":
                missing.append(spec["label"])
        return missing

    def has_minimum_runnable_info(self, session: TaskSession) -> bool:
        return not self.get_missing_fields(session)

    def checklist_text(self) -> str:
        lines = ["已收到需求。请优先按以下研究任务信息清单提供信息：", "", "研究任务信息清单："]
        for spec in FIELD_SPECS:
            lines.append(f"- {spec['label']}（{spec['priority']}）")
        lines.append("")
        lines.append("你可以一次性发完整，也可以先发一部分。我会先整理缺失项，再提醒你运行。")
        return "\n".join(lines)

    def reset_confirmation_text(self) -> str:
        return "已为你清空当前群里的当前研究任务，会按新任务重新收集信息。"

    def build_follow_up_text(self, session: TaskSession) -> str:
        known = self.summarize_known_information(session)
        lines = ["已整理当前研究任务。"]
        if known:
            lines.append("已提供：")
            for label, value in known.items():
                lines.append(f"- {label}：{value}")

        if session.missing_fields:
            lines.append("还缺以下信息：")
            for label in session.missing_fields:
                lines.append(f"- {label}")
            if "指定妈妈画像" in session.missing_fields:
                lines.append("请指定妈妈画像，例如：高线忙碌妈妈 或 M04。")
        else:
            lines.append("信息已收齐，如继续请直接回复“按当前信息运行”。")
        return "\n".join(lines)

    def build_clarification_text(self, session: TaskSession) -> str:
        plan = session.research_plan or {}
        questions = plan.get("clarifying_questions", [])
        missing = plan.get("missing_information", [])
        lines = ["当前资料还不足以发起调研，请先补充以下信息："]
        for item in missing:
            lines.append(f"- {item}")
        if questions:
            lines.append("")
            lines.append("建议你补充：")
            for item in questions:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def summarize_known_information(self, session: TaskSession) -> Dict[str, str]:
        provided = {}
        for field_state in session.fields.values():
            if field_state["status"] == "provided" and field_state["value"] is not None:
                provided[field_state["label"]] = str(field_state["value"])
        return provided

    def build_research_input_payload(self, session: TaskSession) -> Dict[str, Any]:
        return {
            "mode": self._field_text(session, "mode"),
            "question_type": self._field_text(session, "question_type"),
            "persona_id": self._field_text(session, "persona_id"),
            "user_question": self._field_text(session, "user_question"),
            "background_material": self._field_text(session, "background_material"),
            "product_info": self._field_text(session, "product_info"),
            "copy_material": self._field_text(session, "copy_material"),
            "attachments": list(session.attachments),
            "follow_up_context": session.follow_up_context,
        }

    def _field_text(self, session: TaskSession, key: str) -> str:
        value = session.fields[key]["value"]
        return "" if value is None else str(value)

    def _apply_inference(self, session: TaskSession, text: str):
        if session.fields["mode"]["status"] == "missing":
            inferred_mode = self.infer_mode(text)
            if inferred_mode:
                self._set_field_value(session, "mode", inferred_mode)

        if session.fields["question_type"]["status"] == "missing":
            inferred_type = self.infer_question_type(text)
            if inferred_type:
                self._set_field_value(session, "question_type", inferred_type)

        if session.fields["persona_id"]["status"] == "missing":
            inferred_persona = self.infer_persona_id(text)
            if inferred_persona:
                self._set_field_value(session, "persona_id", inferred_persona)

        if session.fields["user_question"]["status"] == "missing":
            inferred_question = self.infer_user_question(text)
            if inferred_question:
                self._set_field_value(session, "user_question", inferred_question)

    def infer_mode(self, text: str) -> str:
        for alias, normalized in MODE_ALIASES.items():
            if alias in text:
                return normalized
        return ""

    def infer_question_type(self, text: str) -> str:
        for alias, normalized in QUESTION_TYPE_ALIASES.items():
            if alias in text:
                return normalized
        if "文案" in text or "卖点" in text:
            return "copy_feedback"
        if "痛点" in text or "怎么解决" in text or "缺少什么" in text:
            return "needs_pain_points"
        if "会不会买" in text or "为什么买" in text or "最大顾虑" in text or "购买决策" in text:
            return "purchase_decision"
        if "概念" in text or "吸引力" in text or "感兴趣" in text:
            return "product_concept"
        return ""

    def infer_persona_id(self, text: str) -> str:
        for alias, persona_id in self.persona_alias_map.items():
            if alias and alias in text:
                return persona_id
        return ""

    def infer_user_question(self, text: str) -> str:
        if not text:
            return ""
        if "妈妈定性研究" in text and len(text) <= 20:
            return ""
        if any(hint in text for hint in QUESTION_HINTS):
            return text.strip()
        return ""

    def _extract_field_updates(self, text: str) -> List[tuple[str, str]]:
        updates: List[tuple[str, str]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            updates.extend(self._extract_line_field_updates(line))
        return updates

    def _extract_line_field_updates(self, line: str) -> List[tuple[str, str]]:
        matches = []
        for match in FIELD_ALIAS_PATTERN.finditer(line):
            start = match.start()
            if start > 0 and line[start - 1] not in FIELD_PREFIX_BOUNDARIES:
                continue
            alias = match.group(0)
            matches.append((FIELD_LABEL_MAP[alias], match.start(), match.end()))

        updates: List[tuple[str, str]] = []
        for index, (key, _, end) in enumerate(matches):
            next_start = matches[index + 1][1] if index + 1 < len(matches) else len(line)
            raw_value = line[end:next_start].strip(FIELD_VALUE_PREFIX_CHARS)
            value = raw_value.strip()
            if value:
                updates.append((key, value))
        return updates

    def _set_field_value(self, session: TaskSession, key: str, value: Any):
        normalized_value = value
        if key == "mode":
            normalized_value = MODE_ALIASES.get(str(value), value)
        elif key == "question_type":
            normalized_value = QUESTION_TYPE_ALIASES.get(
                str(value),
                self.infer_question_type(str(value)) or value,
            )
        elif key == "persona_id":
            normalized_value = self.persona_alias_map.get(str(value), value)

        state = session.fields[key]
        state["status"] = "provided"
        state["value"] = str(normalized_value)

    def _load_persona_alias_map(self, persona_path: Path) -> Dict[str, str]:
        payload = json.loads(persona_path.read_text(encoding="utf-8"))
        alias_map: Dict[str, str] = {}
        for sample in payload.get("samples", []):
            persona_id = sample["segment_id"]
            basic_profile = sample.get("basic_profile", {})
            alias_map.setdefault(persona_id, persona_id)
            alias_map.setdefault(sample.get("segment_name", ""), persona_id)
            alias_map.setdefault(basic_profile.get("nickname", ""), persona_id)
        sorted_aliases = sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True)
        return {alias: persona_id for alias, persona_id in sorted_aliases if alias}

    def _build_session_id(self, group_id: str, conversation_id: str, user_id: str) -> str:
        return f"{group_id}__{conversation_id}__{user_id}"

    def _path_for(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"
