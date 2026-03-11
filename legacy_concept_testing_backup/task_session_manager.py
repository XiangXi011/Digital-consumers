import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


FIELD_SPECS = [
    {"key": "concept_name", "label": "产品/方案名称", "priority": "P0"},
    {"key": "brand", "label": "品牌名", "priority": "P1"},
    {"key": "category", "label": "品类", "priority": "P0"},
    {"key": "core_claims", "label": "核心卖点/功能点", "priority": "P0"},
    {"key": "price", "label": "价格或预计价格带", "priority": "P0"},
    {"key": "packaging_summary", "label": "包装信息", "priority": "P0"},
    {"key": "packaging_image_path", "label": "包装图/主视觉", "priority": "P2"},
    {"key": "target_channels", "label": "目标渠道", "priority": "P1"},
    {"key": "target_audience", "label": "目标人群", "priority": "P1"},
    {"key": "competitors", "label": "竞品/替代方案", "priority": "P1"},
    {"key": "slogan", "label": "主文案/slogan", "priority": "P1"},
    {"key": "ingredients", "label": "成分或关键技术点", "priority": "P2"},
    {"key": "detail_copy", "label": "详情页/种草文案", "priority": "P2"},
    {"key": "validation_questions", "label": "本次最想验证的问题", "priority": "P2"},
]

FIELD_LABEL_MAP = {
    "产品名称": "concept_name",
    "方案名称": "concept_name",
    "产品/方案名称": "concept_name",
    "品牌": "brand",
    "品牌名": "brand",
    "品类": "category",
    "产品类型": "category",
    "核心卖点": "core_claims",
    "功能点": "core_claims",
    "卖点": "core_claims",
    "价格": "price",
    "价格带": "price",
    "包装信息": "packaging_summary",
    "包装描述": "packaging_summary",
    "包装": "packaging_summary",
    "包装图": "packaging_image_path",
    "主视觉": "packaging_image_path",
    "目标渠道": "target_channels",
    "渠道": "target_channels",
    "目标人群": "target_audience",
    "人群": "target_audience",
    "竞品": "competitors",
    "替代方案": "competitors",
    "主文案": "slogan",
    "slogan": "slogan",
    "成分": "ingredients",
    "关键技术点": "ingredients",
    "详情页": "detail_copy",
    "种草文案": "detail_copy",
    "验证问题": "validation_questions",
    "最想验证的问题": "validation_questions",
}

UNKNOWN_TOKENS = ["未定", "未知", "暂缺", "待定", "先不管", "没有", "暂无"]
RUN_CONFIRM_TOKENS = ["按现有", "先跑", "先运行", "先分析", "先出初版", "就按这些", "按当前信息"]
RESET_COMMAND_TOKENS = ["新任务", "重置任务", "清空任务", "重新开始"]
FIELD_ALIASES = sorted(FIELD_LABEL_MAP.items(), key=lambda item: len(item[0]), reverse=True)
FIELD_ALIAS_PATTERN = re.compile("|".join(re.escape(alias) for alias, _ in FIELD_ALIASES))
FIELD_PREFIX_BOUNDARIES = set(" \t,，;；。!！?？、/@")
FIELD_VALUE_PREFIX_CHARS = " ：:，,;；"


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
    last_task_id: Optional[str] = None
    html_report_path: Optional[str] = None
    json_report_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            session_id=data["session_id"],
            group_id=data["group_id"],
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            status=data.get("status", "collecting"),
            checklist_sent=data.get("checklist_sent", False),
            partial_run_authorized=data.get("partial_run_authorized", False),
            fields=data.get("fields") or build_empty_fields(),
            missing_fields=data.get("missing_fields", []),
            last_task_id=data.get("last_task_id"),
            html_report_path=data.get("html_report_path"),
            json_report_path=data.get("json_report_path"),
        )


class TaskSessionManager:
    def __init__(self, session_dir: Path | str, ai_client: Any | None = None):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.ai_client = ai_client

    def has_session_for(self, group_id: str, conversation_id: str, user_id: str) -> bool:
        return self._path_for(self._build_session_id(group_id, conversation_id, user_id)).exists()

    def find_session_for(self, group_id: str, conversation_id: str, user_id: str) -> Optional[TaskSession]:
        path = self._path_for(self._build_session_id(group_id, conversation_id, user_id))
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return TaskSession.from_dict(json.load(handle))

    def get_or_create(self, group_id: str, conversation_id: str, user_id: str) -> TaskSession:
        session_id = self._build_session_id(group_id, conversation_id, user_id)
        path = self._path_for(session_id)
        if path.exists():
            return self.load(session_id)
        session = TaskSession(session_id=session_id, group_id=group_id, conversation_id=conversation_id, user_id=user_id)
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
        with open(self._path_for(session_id), "r", encoding="utf-8") as handle:
            return TaskSession.from_dict(json.load(handle))

    def save(self, session: TaskSession):
        session.missing_fields = self.get_missing_fields(session)
        with open(self._path_for(session.session_id), "w", encoding="utf-8") as handle:
            json.dump(session.to_dict(), handle, ensure_ascii=False, indent=2)

    def update_from_message(self, session: TaskSession, text: str, attachments: Optional[List[str]] = None):
        attachments = attachments or []
        if attachments:
            self._set_field_value(session, "packaging_image_path", str(attachments[0]))
            self._fill_missing_fields_from_images(session, attachments)

        normalized = (text or "").replace("：", ":")
        for key, value in self._extract_field_updates(normalized):
            self._set_field_value(session, key, value)

        session.missing_fields = self.get_missing_fields(session)
        self.save(session)

    def has_run_confirmation(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(token in (text or "") for token in RUN_CONFIRM_TOKENS) or "run" in lowered

    def has_reset_command(self, text: str) -> bool:
        normalized = (text or "").strip()
        return any(token in normalized for token in RESET_COMMAND_TOKENS)

    def get_missing_fields(self, session: TaskSession) -> List[str]:
        missing = []
        for spec in FIELD_SPECS:
            field_state = session.fields[spec["key"]]
            if field_state["status"] == "missing":
                missing.append(spec["label"])
        return missing

    def has_minimum_runnable_info(self, session: TaskSession) -> bool:
        required_keys = ["concept_name", "category", "core_claims", "price"]
        if not all(session.fields[key]["status"] != "missing" for key in required_keys):
            return False

        has_packaging_text = session.fields["packaging_summary"]["status"] != "missing"
        has_packaging_image = session.fields["packaging_image_path"]["status"] != "missing"
        return has_packaging_text or has_packaging_image

    def summarize_known_information(self, session: TaskSession) -> Dict[str, Any]:
        provided = {}
        unknown = {}
        for _, field_state in session.fields.items():
            if field_state["status"] == "provided":
                provided[field_state["label"]] = self._format_display_value(field_state["value"])
            elif field_state["status"] == "unknown":
                unknown[field_state["label"]] = self._format_display_value(field_state["value"])
        return {"provided": provided, "unknown": unknown}

    def checklist_text(self) -> str:
        lines = ["已收到需求。请优先按以下完整资料清单提供信息：", "", "完整资料清单："]
        for spec in FIELD_SPECS:
            lines.append(f"- {spec['label']}（{spec['priority']}）")
        lines.append("")
        lines.append("你可以一次性发送，也可以先发一部分。我会先整理缺失项，再询问是否按当前已知信息运行。")
        return "\n".join(lines)

    def reset_confirmation_text(self) -> str:
        return "已为你清空当前群里的当前任务，会按新任务重新收集资料。"

    def build_follow_up_text(self, session: TaskSession) -> str:
        known = self.summarize_known_information(session)
        lines = ["已整理当前信息。"]
        if known["provided"]:
            lines.append("已提供：")
            for label, value in known["provided"].items():
                lines.append(f"- {label}：{value}")
        if known["unknown"]:
            lines.append("已标记为未定/未知：")
            for label, value in known["unknown"].items():
                lines.append(f"- {label}：{value}")
        if session.missing_fields:
            lines.append("还缺以下信息：")
            for label in session.missing_fields:
                lines.append(f"- {label}")
        lines.append("是否按当前已知信息先运行分析？如果要继续，请直接回复“按现有资料运行”。")
        return "\n".join(lines)

    def build_concept_payload(self, session: TaskSession) -> Dict[str, Any]:
        price_value = session.fields["price"]["value"] or "39.9"
        price_match = re.search(r"\d+(?:\.\d+)?", str(price_value))
        numeric_price = float(price_match.group()) if price_match else 39.9

        core_claims = session.fields["core_claims"]["value"] or []
        if isinstance(core_claims, str):
            core_claims = self._split_list_values(core_claims)

        packaging_summary = self._field_text(session, "packaging_summary", "包装信息待补充")
        if (
            session.fields["packaging_summary"]["status"] == "missing"
            and session.fields["packaging_image_path"]["status"] != "missing"
        ):
            packaging_summary = "Uploaded packaging image is available for visual analysis."

        return {
            "concept_name": self._field_text(session, "concept_name", "未命名方案"),
            "brand": self._field_text(session, "brand", "未提供品牌"),
            "category": self._field_text(session, "category", "未提供品类"),
            "price": numeric_price,
            "core_claims": core_claims or ["卖点待补充"],
            "packaging_summary": packaging_summary,
            "tagline": self._field_text(session, "slogan", ""),
            "target_channels": self._field_list(session, "target_channels"),
            "competitive_anchors": self._field_list(session, "competitors"),
            "context_notes": self._build_context_notes(session),
            "missing_fields": list(session.missing_fields),
            "packaging_image_path": self._field_text(session, "packaging_image_path", ""),
        }

    def _build_context_notes(self, session: TaskSession) -> str:
        parts = []
        validation = self._field_text(session, "validation_questions", "")
        if validation:
            parts.append(f"重点验证问题：{validation}")
        ingredients = self._field_text(session, "ingredients", "")
        if ingredients:
            parts.append(f"成分/技术点：{ingredients}")
        detail_copy = self._field_text(session, "detail_copy", "")
        if detail_copy:
            parts.append(f"详情页/种草文案：{detail_copy}")
        if session.partial_run_authorized:
            parts.append("用户已明确授权按当前已知信息运行。")
        return "\n".join(parts)

    def _field_text(self, session: TaskSession, key: str, default: str) -> str:
        value = session.fields[key]["value"]
        if value is None:
            return default
        return str(value)

    def _field_list(self, session: TaskSession, key: str) -> List[str]:
        value = session.fields[key]["value"]
        if not value:
            return []
        if isinstance(value, list):
            return value
        return self._split_list_values(str(value))

    def _fill_missing_fields_from_images(self, session: TaskSession, attachments: List[str]):
        if not self.ai_client or not hasattr(self.ai_client, "extract_product_fields_from_image"):
            return

        for image_path in attachments:
            extracted = self.ai_client.extract_product_fields_from_image(Path(image_path))
            for key, value in (extracted.get("fields") or {}).items():
                if key not in session.fields:
                    continue
                if session.fields[key]["status"] != "missing":
                    continue
                if self._is_empty_value(value):
                    continue
                self._set_field_value(session, key, value)

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
            matches.append((alias, FIELD_LABEL_MAP[alias], match.start(), match.end()))

        updates: List[tuple[str, str]] = []
        for index, (_, key, _, end) in enumerate(matches):
            next_start = matches[index + 1][2] if index + 1 < len(matches) else len(line)
            raw_value = line[end:next_start].strip(FIELD_VALUE_PREFIX_CHARS)
            value = raw_value.strip()
            if not value:
                continue
            updates.append((key, value))
        return updates

    def _set_field_value(self, session: TaskSession, key: str, value: Any):
        if value is None:
            return

        state = session.fields[key]
        if isinstance(value, str) and any(token in value for token in UNKNOWN_TOKENS):
            state["status"] = "unknown"
            state["value"] = value
            return

        if key in {"core_claims", "target_channels", "competitors"}:
            state["status"] = "provided"
            if isinstance(value, list):
                state["value"] = [str(item).strip() for item in value if str(item).strip()]
            else:
                state["value"] = self._split_list_values(str(value))
            return

        state["status"] = "provided"
        if isinstance(value, list):
            state["value"] = "，".join(str(item).strip() for item in value if str(item).strip())
        else:
            state["value"] = str(value)

    def _resolve_field_key(self, label: str) -> Optional[str]:
        for candidate, key in FIELD_LABEL_MAP.items():
            if candidate in label:
                return key
        return None

    def _split_list_values(self, value: str) -> List[str]:
        return [item.strip() for item in re.split(r"[；;，,、\n]", value) if item.strip()]

    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, list):
            return not any(str(item).strip() for item in value)
        return not str(value).strip()

    def _format_display_value(self, value: Any) -> str:
        if isinstance(value, list):
            return "；".join(str(item).strip() for item in value if str(item).strip())
        return str(value)

    def _build_session_id(self, group_id: str, conversation_id: str, user_id: str) -> str:
        return f"{group_id}__{conversation_id}__{user_id}"

    def _path_for(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"
