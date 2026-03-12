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
    "mode": "mode",
    "研究问题": "question_type",
    "问题类型": "question_type",
    "question_type": "question_type",
    "指定妈妈画像": "persona_id",
    "妈妈画像": "persona_id",
    "画像": "persona_id",
    "persona": "persona_id",
    "persona_id": "persona_id",
    "用户问题": "user_question",
    "用户提问": "user_question",
    "原始问题": "user_question",
    "question": "user_question",
    "user_question": "user_question",
    "背景资料": "background_material",
    "背景": "background_material",
    "background": "background_material",
    "background_material": "background_material",
    "产品信息": "product_info",
    "产品资料": "product_info",
    "产品": "product_info",
    "product": "product_info",
    "product_info": "product_info",
    "文案或卖点": "copy_material",
    "文案和卖点": "copy_material",
    "文案": "copy_material",
    "卖点": "copy_material",
    "copy": "copy_material",
    "copy_material": "copy_material",
}

MODE_ALIASES = {
    "多人模式": "multi",
    "多人": "multi",
    "8类妈妈": "multi",
    "八类妈妈": "multi",
    "multi": "multi",
    "multi mode": "multi",
    "单人模式": "single",
    "单人": "single",
    "single": "single",
    "single mode": "single",
}

QUESTION_TYPE_ALIASES = {
    "产品概念": "product_concept",
    "product concept": "product_concept",
    "购买决策": "purchase_decision",
    "purchase decision": "purchase_decision",
    "需求痛点": "needs_pain_points",
    "pain points": "needs_pain_points",
    "needs": "needs_pain_points",
    "文案和卖点反馈": "copy_feedback",
    "文案反馈": "copy_feedback",
    "卖点反馈": "copy_feedback",
    "copy feedback": "copy_feedback",
    "copy": "copy_feedback",
}

RUN_CONFIRM_TOKENS = [
    "按当前信息运行",
    "开始分析",
    "运行",
    "开始跑",
    "开始研究",
    "run",
    "start",
]
ASSUMPTION_RUN_TOKENS = [
    "先按当前信息跑一次",
    "先按现有资料跑一次",
    "先跑一次",
    "可以先跑",
    "可以先假设",
    "带假设先跑",
    "run once with assumptions",
    "run with assumptions",
    "assume and run",
    "use assumptions and run",
]
RESET_COMMAND_TOKENS = [
    "新任务",
    "重置任务",
    "清空任务",
    "重新开始",
    "reset",
    "new task",
]
QUESTION_HINTS = [
    "?",
    "？",
    "会不会",
    "有没有",
    "为什么",
    "什么",
    "顾虑",
    "痛点",
    "文案",
    "卖点",
    "吸引力",
    "why",
    "what",
    "which",
    "will",
]
FIELD_ALIASES = sorted(FIELD_LABEL_MAP.items(), key=lambda item: len(item[0]), reverse=True)
FIELD_ALIAS_PATTERN = re.compile("|".join(re.escape(alias) for alias, _ in FIELD_ALIASES), re.IGNORECASE)
FIELD_PREFIX_BOUNDARIES = set(" \t,，：:？。?!；;()（）[]【】")
FIELD_VALUE_PREFIX_CHARS = " ：:；;，,。"


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
    allow_assumption_run: bool = False
    fields: Dict[str, Dict[str, Any]] = field(default_factory=build_empty_fields)
    missing_fields: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    follow_up_context: str = ""
    planner_result: Dict[str, Any] = field(default_factory=dict)
    last_task_id: Optional[str] = None
    html_report_path: Optional[str] = None
    json_report_path: Optional[str] = None

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
                status="collecting",
                checklist_sent=False,
                partial_run_authorized=False,
                allow_assumption_run=False,
                fields=fields,
                missing_fields=[],
                attachments=data.get("attachments", []),
                follow_up_context="",
                planner_result={},
                last_task_id=None,
                html_report_path=None,
                json_report_path=None,
            )
        return cls(
            session_id=data["session_id"],
            group_id=data["group_id"],
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            status=data.get("status", "collecting"),
            checklist_sent=data.get("checklist_sent", False),
            partial_run_authorized=data.get("partial_run_authorized", False),
            allow_assumption_run=data.get("allow_assumption_run", False),
            fields=fields,
            missing_fields=data.get("missing_fields", []),
            attachments=data.get("attachments", []),
            follow_up_context=data.get("follow_up_context", ""),
            planner_result=data.get("planner_result", {}),
            last_task_id=data.get("last_task_id"),
            html_report_path=data.get("html_report_path"),
            json_report_path=data.get("json_report_path"),
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
        session = TaskSession(session_id=session_id, group_id=group_id, conversation_id=conversation_id, user_id=user_id)
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
        normalized_text = (text or "").strip()
        changed = False

        for attachment in attachments or []:
            if attachment not in session.attachments:
                session.attachments.append(attachment)
                changed = True

        for key, value in self._extract_field_updates(normalized_text):
            changed = self._set_field_value(session, key, value) or changed

        changed = self._apply_inference(session, normalized_text) or changed

        if self.has_assumption_authorization(normalized_text):
            session.allow_assumption_run = True
        elif changed:
            session.allow_assumption_run = False

        if changed:
            session.planner_result = {}
            if session.status == "awaiting_clarification":
                session.status = "collecting"

        self.save(session)

    def has_run_confirmation(self, text: str) -> bool:
        normalized = (text or "").strip()
        lowered = normalized.lower()
        return lowered == "run" or any(token in normalized or token in lowered for token in RUN_CONFIRM_TOKENS)

    def has_assumption_authorization(self, text: str) -> bool:
        normalized = (text or "").strip()
        lowered = normalized.lower()
        return any(token in normalized or token in lowered for token in ASSUMPTION_RUN_TOKENS)

    def has_reset_command(self, text: str) -> bool:
        normalized = (text or "").strip()
        lowered = normalized.lower()
        return any(token in normalized or token in lowered for token in RESET_COMMAND_TOKENS)

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
        lines = [
            "已收到需求。请优先按以下研究任务信息清单提供信息：",
            "",
            "研究任务信息清单：",
        ]
        for spec in FIELD_SPECS:
            lines.append(f"- {spec['label']}（{spec['priority']}）")
        lines.append("")
        lines.append("你可以一次性发完整，也可以先发一部分。我会先整理缺失项，再提醒你运行。")
        return "\n".join(lines)

    def reset_confirmation_text(self) -> str:
        return "已为你清空当前群里的当前研究任务，会按新任务重新收集信息。"

    def build_follow_up_text(self, session: TaskSession) -> str:
        known = self.summarize_known_information(session)
        if session.status == "awaiting_clarification" and session.planner_result:
            return self._build_planner_follow_up_text(session, known)

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
                lines.append("请指定妈妈画像，例如：高线忙碌妈 或 M04。")
        else:
            lines.append("信息已收齐，如继续请直接回复“按当前信息运行”。")
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
            "allow_assumption_run": session.allow_assumption_run,
            "planner_result": dict(session.planner_result),
        }

    def _field_text(self, session: TaskSession, key: str) -> str:
        value = session.fields[key]["value"]
        return "" if value is None else str(value)

    def _apply_inference(self, session: TaskSession, text: str) -> bool:
        changed = False
        if session.fields["mode"]["status"] == "missing":
            inferred_mode = self.infer_mode(text)
            if inferred_mode:
                changed = self._set_field_value(session, "mode", inferred_mode) or changed

        if session.fields["question_type"]["status"] == "missing":
            inferred_type = self.infer_question_type(text)
            if inferred_type:
                changed = self._set_field_value(session, "question_type", inferred_type) or changed

        if session.fields["persona_id"]["status"] == "missing":
            inferred_persona = self.infer_persona_id(text)
            if inferred_persona:
                changed = self._set_field_value(session, "persona_id", inferred_persona) or changed

        if session.fields["user_question"]["status"] == "missing":
            inferred_question = self.infer_user_question(text)
            if inferred_question:
                changed = self._set_field_value(session, "user_question", inferred_question) or changed

        return changed

    def infer_mode(self, text: str) -> str:
        lowered = text.lower()
        for alias, normalized in MODE_ALIASES.items():
            if alias in text or alias in lowered:
                return normalized
        return ""

    def infer_question_type(self, text: str) -> str:
        lowered = text.lower()
        for alias, normalized in QUESTION_TYPE_ALIASES.items():
            if alias in text or alias in lowered:
                return normalized
        if "文案" in text or "卖点" in text or "copy" in lowered:
            return "copy_feedback"
        if "痛点" in text or "怎么解决" in text or "还缺什么" in text or "pain" in lowered:
            return "needs_pain_points"
        if "会不会买" in text or "为什么买" in text or "最大顾虑" in text or "购买决策" in text or "buy" in lowered:
            return "purchase_decision"
        if "概念" in text or "吸引力" in text or "感兴趣" in text or "concept" in lowered:
            return "product_concept"
        return ""

    def infer_persona_id(self, text: str) -> str:
        lowered = text.lower()
        for alias, persona_id in self.persona_alias_map.items():
            if alias and (alias in text or alias.lower() in lowered):
                return persona_id
        return ""

    def infer_user_question(self, text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return ""
        lowered = normalized.lower()
        if "妈妈定性研究" in normalized and len(normalized) <= 20:
            return ""
        if any(hint in normalized or hint in lowered for hint in QUESTION_HINTS):
            return normalized
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
            key = self._resolve_field_alias(alias)
            if key:
                matches.append((key, match.start(), match.end()))

        updates: List[tuple[str, str]] = []
        for index, (key, _, end) in enumerate(matches):
            next_start = matches[index + 1][1] if index + 1 < len(matches) else len(line)
            raw_value = line[end:next_start].strip(FIELD_VALUE_PREFIX_CHARS)
            value = raw_value.strip()
            if value:
                updates.append((key, value))
        return updates

    def _resolve_field_alias(self, alias: str) -> str:
        return FIELD_LABEL_MAP.get(alias, FIELD_LABEL_MAP.get(alias.lower(), ""))

    def _set_field_value(self, session: TaskSession, key: str, value: Any) -> bool:
        normalized_value = self._normalize_field_value(key, value)
        state = session.fields[key]
        next_value = str(normalized_value)
        changed = state["status"] != "provided" or state["value"] != next_value
        state["status"] = "provided"
        state["value"] = next_value
        return changed

    def _normalize_field_value(self, key: str, value: Any) -> str:
        text = str(value).strip()
        lowered = text.lower()
        if key == "mode":
            return MODE_ALIASES.get(text, MODE_ALIASES.get(lowered, text))
        if key == "question_type":
            return QUESTION_TYPE_ALIASES.get(text, QUESTION_TYPE_ALIASES.get(lowered, self.infer_question_type(text) or text))
        if key == "persona_id":
            return self.persona_alias_map.get(text, self.persona_alias_map.get(lowered, text))
        return text

    def _build_planner_follow_up_text(self, session: TaskSession, known: Dict[str, str]) -> str:
        plan = session.planner_result
        lines = ["研究助理已先完成需求拆解。"]
        if known:
            lines.append("当前已知信息：")
            for label, value in known.items():
                lines.append(f"- {label}：{value}")

        missing_information = list(plan.get("missing_information") or [])
        clarification_questions = list(plan.get("clarification_questions") or [])
        assumptions = list(plan.get("assumptions_if_run_now") or [])

        if missing_information:
            lines.append("还需要补充：")
            for item in missing_information:
                lines.append(f"- {item}")

        if clarification_questions:
            lines.append("请先回答以下问题：")
            for item in clarification_questions:
                lines.append(f"- {item}")

        if assumptions:
            lines.append("如果你接受先基于以下假设跑第一轮，也可以直接授权：")
            for item in assumptions:
                lines.append(f"- {item}")
            lines.append("可回复“先按当前信息跑一次”或“run once with assumptions”。")
        return "\n".join(lines)

    def _load_persona_alias_map(self, persona_path: Path) -> Dict[str, str]:
        payload = json.loads(persona_path.read_text(encoding="utf-8"))
        alias_map: Dict[str, str] = {}
        for sample in payload.get("samples", []):
            persona_id = sample["segment_id"]
            basic_profile = sample.get("basic_profile", {})
            aliases = {
                persona_id,
                sample.get("segment_name", ""),
                basic_profile.get("nickname", ""),
            }
            for alias in aliases:
                if not alias:
                    continue
                alias_map.setdefault(alias, persona_id)
                alias_map.setdefault(alias.lower(), persona_id)
        sorted_aliases = sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True)
        return {alias: persona_id for alias, persona_id in sorted_aliases if alias}

    def _build_session_id(self, group_id: str, conversation_id: str, user_id: str) -> str:
        return f"{group_id}__{conversation_id}__{user_id}"

    def _path_for(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"
