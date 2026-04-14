import json
import logging
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.paths import REPO_ROOT


logger = logging.getLogger(__name__)


FIELD_SPECS = [
    {"key": "mode", "label": "\u6a21\u5f0f", "priority": "P0"},
    {"key": "question_type", "label": "\u7814\u7a76\u95ee\u9898", "priority": "P0"},
    {"key": "persona_id", "label": "\u6307\u5b9a\u5988\u5988\u753b\u50cf", "priority": "P0"},
    {"key": "user_question", "label": "\u7528\u6237\u95ee\u9898", "priority": "P0"},
    {"key": "background_material", "label": "\u80cc\u666f\u8d44\u6599", "priority": "P1"},
    {"key": "product_info", "label": "\u4ea7\u54c1\u4fe1\u606f", "priority": "P0"},
    {"key": "copy_material", "label": "\u6587\u6848\u6216\u5356\u70b9", "priority": "P1"},
    {"key": "price_test_mode", "label": "\u4ef7\u683c\u6d4b\u8bd5\u65b9\u5f0f", "priority": "P0"},
    {"key": "price_range", "label": "\u4ef7\u683c\u533a\u95f4", "priority": "P0"},
    {"key": "benchmark_reference", "label": "\u5bf9\u6807\u53c2\u8003", "priority": "P1"},
    {"key": "pack_size_or_volume", "label": "\u89c4\u683c\u6216\u5bb9\u91cf", "priority": "P1"},
    {"key": "price_anchor_type", "label": "\u4ef7\u683c\u951a\u70b9\u7c7b\u578b", "priority": "P1"},
    {"key": "target_age", "label": "\u76ee\u6807\u5e74\u9f84", "priority": "P1"},
    {"key": "channel", "label": "\u6e20\u9053", "priority": "P1"},
    {"key": "brand", "label": "\u54c1\u724c", "priority": "P1"},
    {"key": "enable_group_discussion", "label": "\u5c0f\u7ec4\u8ba8\u8bba", "priority": "P1"},
    {"key": "enable_deep_dive", "label": "\u6df1\u5ea6\u8bbf\u8c08", "priority": "P1"},
]

FIELD_LABELS = {spec["key"]: spec["label"] for spec in FIELD_SPECS}

FIELD_LABEL_MAP = {
    "\u6a21\u5f0f": "mode",
    "\u7814\u7a76\u95ee\u9898": "question_type",
    "\u6307\u5b9a\u5988\u5988\u753b\u50cf": "persona_id",
    "\u5988\u5988\u753b\u50cf": "persona_id",
    "\u753b\u50cf": "persona_id",
    "\u7528\u6237\u95ee\u9898": "user_question",
    "\u95ee\u9898": "user_question",
    "\u80cc\u666f\u8d44\u6599": "background_material",
    "\u80cc\u666f": "background_material",
    "\u4ea7\u54c1\u4fe1\u606f": "product_info",
    "\u4ea7\u54c1": "product_info",
    "\u6587\u6848\u6216\u5356\u70b9": "copy_material",
    "\u6587\u6848": "copy_material",
    "\u5356\u70b9": "copy_material",
    "\u4ef7\u683c\u6d4b\u8bd5\u65b9\u5f0f": "price_test_mode",
    "\u6d4b\u4ef7\u65b9\u5f0f": "price_test_mode",
    "\u4ef7\u683c\u533a\u95f4": "price_range",
    "\u5bf9\u6807\u53c2\u8003": "benchmark_reference",
    "\u5bf9\u6807": "benchmark_reference",
    "\u53c2\u8003\u7ade\u54c1": "benchmark_reference",
    "\u89c4\u683c\u6216\u5bb9\u91cf": "pack_size_or_volume",
    "\u89c4\u683c": "pack_size_or_volume",
    "\u5bb9\u91cf": "pack_size_or_volume",
    "\u4ef7\u683c\u951a\u70b9\u7c7b\u578b": "price_anchor_type",
    "\u4ef7\u683c\u951a\u70b9": "price_anchor_type",
    "\u76ee\u6807\u5e74\u9f84": "target_age",
    "\u5e74\u9f84": "target_age",
    "\u6e20\u9053": "channel",
    "\u54c1\u724c": "brand",
}

MODE_ALIASES = {
    "\u591a\u4eba\u6a21\u5f0f": "multi",
    "\u591a\u4eba": "multi",
    "\u516b\u7c7b\u5988\u5988": "multi",
    "8\u7c7b\u5988\u5988": "multi",
    "multi": "multi",
    "\u5355\u4eba\u6a21\u5f0f": "single",
    "\u5355\u4eba": "single",
    "single": "single",
}

QUESTION_TYPE_ALIASES = {
    "\u4ea7\u54c1\u6982\u5ff5": "product_concept",
    "product_concept": "product_concept",
    "\u8d2d\u4e70\u51b3\u7b56": "purchase_decision",
    "purchase_decision": "purchase_decision",
    "\u9700\u6c42\u75db\u70b9": "needs_pain_points",
    "needs_pain_points": "needs_pain_points",
    "\u6587\u6848\u548c\u5356\u70b9\u53cd\u9988": "copy_feedback",
    "\u6587\u6848\u53cd\u9988": "copy_feedback",
    "\u5356\u70b9\u53cd\u9988": "copy_feedback",
    "copy_feedback": "copy_feedback",
    "A/B\u6d4b\u8bd5": "ab_test",
    "AB\u6d4b\u8bd5": "ab_test",
    "ab_test": "ab_test",
    "ab test": "ab_test",
    "\u4ef7\u683c\u6d4b\u8bd5": "price_test",
    "\u4ef7\u683c\u654f\u611f\u5ea6": "price_test",
    "price_test": "price_test",
}

PRICE_TEST_MODE_ALIASES = {
    "absolute_price": "absolute_price",
    "\u7edd\u5bf9\u4ef7\u683c": "absolute_price",
    "\u76f4\u63a5\u6d4b\u4ef7": "absolute_price",
    "\u5355\u4ef7\u6d4b\u8bd5": "absolute_price",
    "relative_price": "relative_price",
    "\u76f8\u5bf9\u4ef7\u683c": "relative_price",
    "\u5bf9\u6807\u4ef7\u683c": "relative_price",
    "\u7ade\u54c1\u5bf9\u6bd4": "relative_price",
    "promo_vs_daily": "promo_vs_daily",
    "\u4fc3\u9500\u4ef7vs\u65e5\u5e38\u4ef7": "promo_vs_daily",
    "\u4fc3\u9500\u4e0e\u65e5\u5e38\u4ef7": "promo_vs_daily",
}

PRICE_ANCHOR_ALIASES = {
    "competitor": "competitor",
    "\u7ade\u54c1": "competitor",
    "category_norm": "category_norm",
    "\u7c7b\u76ee\u5e38\u89c4": "category_norm",
    "historical_price": "historical_price",
    "\u5386\u53f2\u4ef7\u683c": "historical_price",
    "promo_anchor": "promo_anchor",
    "\u4fc3\u9500\u951a\u70b9": "promo_anchor",
}

RUN_CONFIRM_TOKENS = [
    "\u6309\u5f53\u524d\u4fe1\u606f\u8fd0\u884c",
    "\u5f00\u59cb\u5206\u6790",
    "\u8fd0\u884c",
    "\u5f00\u59cb\u8dd1",
    "\u5f00\u59cb\u7814\u7a76",
    "\u5f00\u59cb",
    "\u53ef\u4ee5\u5f00\u59cb",
    "\u53ef\u4ee5\u8dd1\u4e86",
    "\u76f4\u63a5\u8dd1",
    "go",
    "start",
]
WEAK_AFFIRM_TOKENS = [
    "\u597d",
    "\u53ef\u4ee5",
    "\u55ef",
    "\u597d\u7684",
    "\u884c",
    "ok",
    "OK",
    "\u53ef\u4ee5\u4e86",
    "\u660e\u767d",
    "\u6536\u5230",
]
DENIAL_TOKENS = ["\u7b49\u7b49", "\u5148\u522b", "\u4e0d\u8981", "\u6682\u505c", "\u505c", "\u522b\u8dd1", "\u53d6\u6d88"]
AUTHORIZATION_WINDOW_SECONDS = 300
RESET_COMMAND_TOKENS = ["\u65b0\u4efb\u52a1", "\u91cd\u7f6e\u4efb\u52a1", "\u6e05\u7a7a\u4efb\u52a1", "\u91cd\u65b0\u5f00\u59cb"]
QUESTION_HINTS = [
    "?",
    "\uff1f",
    "\u4f1a\u4e0d\u4f1a",
    "\u6709\u6ca1\u6709",
    "\u4e3a\u4ec0\u4e48",
    "\u4ec0\u4e48",
    "\u987e\u8651",
    "\u75db\u70b9",
    "\u6587\u6848",
    "\u5356\u70b9",
    "\u5438\u5f15\u529b",
]
CUSTOM_QUESTION_HINTS = [hint for hint in QUESTION_HINTS if hint not in {"\u6587\u6848", "\u5356\u70b9"}]
FIELD_ALIASES = sorted(FIELD_LABEL_MAP.items(), key=lambda item: len(item[0]), reverse=True)
FIELD_ALIAS_PATTERN = re.compile("|".join(re.escape(alias) for alias, _ in FIELD_ALIASES))
FIELD_PREFIX_BOUNDARIES = set(" \t,:\uff1a\uff0c\u3002\uff1b;!?\uff01\uff1f[]\u3010\u3011()\uff08\uff09")
FIELD_VALUE_PREFIX_CHARS = " \uff1a:;\uff1b\uff0c, \t"
SOURCE_LINK_PATTERN = re.compile(r"https?://[^\s<>\]\)]+")


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
    source_links: List[str] = field(default_factory=list)
    custom_questions: List[str] = field(default_factory=list)
    product_context_notes: List[str] = field(default_factory=list)
    follow_up_context: str = ""
    last_task_id: Optional[str] = None
    html_report_path: Optional[str] = None
    json_report_path: Optional[str] = None
    research_plan: Optional[Dict[str, Any]] = None
    business_brief: Optional[Dict[str, Any]] = None
    readiness_decision: Optional[Dict[str, Any]] = None
    authorization_requested_at: Optional[float] = None
    authorization_requested_by: Optional[str] = None
    live_snapshot_refs: List[str] = field(default_factory=list)
    frozen_snapshot_refs: List[str] = field(default_factory=list)
    retention_policy: Dict[str, Any] = field(default_factory=dict)
    metrics_path: Optional[str] = None
    suspended_messages: List[str] = field(default_factory=list)

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
                source_links=data.get("source_links", []),
                custom_questions=data.get("custom_questions", []),
                product_context_notes=data.get("product_context_notes", []),
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
            source_links=data.get("source_links", []),
            custom_questions=data.get("custom_questions", []),
            product_context_notes=data.get("product_context_notes", []),
            follow_up_context=data.get("follow_up_context", ""),
            last_task_id=data.get("last_task_id"),
            html_report_path=data.get("html_report_path"),
            json_report_path=data.get("json_report_path"),
            research_plan=data.get("research_plan"),
            business_brief=data.get("business_brief"),
            readiness_decision=data.get("readiness_decision"),
            authorization_requested_at=data.get("authorization_requested_at"),
            authorization_requested_by=data.get("authorization_requested_by"),
            live_snapshot_refs=data.get("live_snapshot_refs", []),
            frozen_snapshot_refs=data.get("frozen_snapshot_refs", []),
            retention_policy=data.get("retention_policy", {}),
            metrics_path=data.get("metrics_path"),
            suspended_messages=data.get("suspended_messages", []),
        )


class TaskSessionManager:
    def __init__(
        self,
        session_dir: Path | str,
        persona_path: Path | str,
        ai_client: Any | None = None,
        store: Any | None = None,
    ):
        from backend.infra.runtime_artifacts import RuntimeArtifactStore

        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.ai_client = ai_client
        self.store = store  # KeyValueStore for dedup/ordering/suspend
        self.artifact_store = RuntimeArtifactStore(self.session_dir.parent)
        self.persona_alias_map = self._load_persona_alias_map(Path(persona_path))
        self._file_locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

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

    def start_new_task(self, session: TaskSession) -> TaskSession:
        session.status = "collecting"
        session.partial_run_authorized = False
        session.fields = build_empty_fields()
        session.missing_fields = []
        session.attachments = []
        session.source_links = []
        session.custom_questions = []
        session.product_context_notes = []
        session.follow_up_context = ""
        session.last_task_id = None
        session.html_report_path = None
        session.json_report_path = None
        session.research_plan = None
        session.business_brief = None
        session.readiness_decision = None
        session.authorization_requested_at = None
        session.authorization_requested_by = None
        session.metrics_path = None
        session.suspended_messages = []
        self.save(session)
        return session

    def load(self, session_id: str) -> TaskSession:
        return TaskSession.from_dict(
            json.loads(self._path_for(session_id).read_text(encoding="utf-8"))
        )

    def _get_session_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a specific session to prevent concurrent file access."""
        with self._global_lock:
            if session_id not in self._file_locks:
                self._file_locks[session_id] = threading.Lock()
            return self._file_locks[session_id]

    def save(self, session: TaskSession):
        session_lock = self._get_session_lock(session.session_id)
        with session_lock:
            current_path = self._path_for(session.session_id)
            if current_path.exists():
                previous = TaskSession.from_dict(json.loads(current_path.read_text(encoding="utf-8")))
                self._validate_status_transition(previous.status, session.status)
            session.missing_fields = self.get_missing_fields(session)
            if not session.retention_policy:
                from backend.infra.privacy_utils import build_retention_policy

                session.retention_policy = build_retention_policy()
            current_path.write_text(
                json.dumps(self._serialize_for_storage(session), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def update_from_message(self, session: TaskSession, text: str, attachments: Optional[List[str]] = None) -> TaskSession:
        """Update session from message text and attachments. Returns the updated session."""
        normalized_text = (text or "").strip()
        for attachment in attachments or []:
            if attachment not in session.attachments:
                session.attachments.append(attachment)

        self._append_unique_items(session.source_links, self._extract_source_links(normalized_text))
        self._append_unique_items(session.custom_questions, self._extract_custom_questions(normalized_text))

        for key, value in self._extract_field_updates(normalized_text):
            self._set_field_value(session, key, value)

        # OCR-first enrichment from image attachments (user text has higher priority)
        self._apply_attachment_enrichment_v2(session, attachments or [])

        self._apply_inference(session, normalized_text)
        self.save(session)
        # Return the same session object (already updated) to avoid reloading
        # and potential race conditions with concurrent modifications
        return session

    def preview_fields_from_text(self, text: str) -> Dict[str, Dict[str, Any]]:
        preview_session = TaskSession(
            session_id="preview",
            group_id="preview",
            conversation_id="preview",
            user_id="preview",
        )
        normalized_text = (text or "").strip()
        for key, value in self._extract_field_updates(normalized_text):
            self._set_field_value(preview_session, key, value)
        self._apply_inference(preview_session, normalized_text)
        preview_session.missing_fields = self.get_missing_fields(preview_session)
        return preview_session.fields

    def has_run_confirmation(self, text: str) -> bool:
        normalized = (text or "").strip()
        lowered = normalized.lower()
        return any(token in normalized for token in RUN_CONFIRM_TOKENS) or lowered == "run"

    def classify_authorization(
        self, text: str, user_id: str, event: dict, session: Optional["TaskSession"] = None,
    ) -> str:
        import time

        normalized = (text or "").strip()
        lowered = normalized.lower()
        is_direct = event.get("is_bot_mentioned", False) or event.get("is_private_chat", False)

        if any(token in normalized for token in DENIAL_TOKENS):
            return "denial"

        has_run_token = any(token in normalized for token in RUN_CONFIRM_TOKENS) or lowered == "run"
        if has_run_token:
            if is_direct:
                return "strong_affirm"
            return "none"

        if lowered in [token.lower() for token in WEAK_AFFIRM_TOKENS]:
            if not is_direct:
                return "none"
            if session is None or self._normalize_status(session.status) != "awaiting_authorization":
                return "none"
            from backend.infra.privacy_utils import matches_hashed_identifier

            if not matches_hashed_identifier(session.authorization_requested_by, user_id):
                return "none"
            if session.authorization_requested_at is None:
                return "none"
            now = event.get("create_ts")
            if now is None:
                now = time.time() * 1000
            elapsed_seconds = (float(now) - session.authorization_requested_at) / 1000
            if elapsed_seconds > AUTHORIZATION_WINDOW_SECONDS:
                return "none"
            return "weak_affirm"

        # Fuzzy authorization: allow affirmative intent if user mentions bot in group
        if is_direct and any(token in lowered for token in ["\u8dd1", "\u5f00\u59cb", "\u53ef\u4ee5", "\u6267\u884c", "\u7ee7\u7eed", "\u786e\u8ba4"]):
            if session is not None and self._normalize_status(session.status) == "awaiting_authorization":
                return "weak_affirm"

        return "none"

    def save_live_snapshot(self, session: TaskSession, stage: str, payload: Dict[str, Any]) -> str:
        ref = self.artifact_store.save_live(
            session_id=session.session_id,
            stage=stage,
            payload=self._snapshot_payload(session, payload),
            metadata={"retention_policy": session.retention_policy or self._default_retention_policy()},
        )
        session.live_snapshot_refs.append(ref)
        self.save(session)
        return ref

    def save_frozen_snapshot(self, session: TaskSession, stage: str, payload: Dict[str, Any]) -> str:
        from backend.infra.system_fingerprint import collect_version_bundle

        ref = self.artifact_store.save_frozen(
            session_id=session.session_id,
            stage=stage,
            payload=self._snapshot_payload(session, payload),
            version_bundle=collect_version_bundle(
                REPO_ROOT,
                ai_client=self.ai_client,
            ),
        )
        session.frozen_snapshot_refs.append(ref)
        self.save(session)
        return ref

    def save_metrics_artifact(self, task_id: str, metrics: Dict[str, Any]) -> str:
        return self.artifact_store.save_metrics(task_id=task_id, metrics=metrics)

    def has_reset_command(self, text: str) -> bool:
        normalized = (text or "").strip()
        return any(token in normalized for token in RESET_COMMAND_TOKENS)

    def get_missing_fields(self, session: TaskSession) -> List[str]:
        required_keys = {"mode", "question_type", "user_question", "product_info"}
        mode = self._field_text(session, "mode")
        question_type = self._field_text(session, "question_type")
        price_test_mode = self._field_text(session, "price_test_mode")

        if mode == "single":
            required_keys.add("persona_id")
        if question_type in {"copy_feedback", "ab_test"}:
            required_keys.add("copy_material")
        if question_type == "price_test":
            required_keys.update({"price_test_mode", "price_range"})
            if price_test_mode == "relative_price":
                required_keys.add("benchmark_reference")
            if price_test_mode == "promo_vs_daily":
                required_keys.add("price_anchor_type")

        missing = []
        for key in required_keys:
            value = self._field_text(session, key)
            if not value:
                missing.append(FIELD_LABELS[key])
        ordered_labels = [spec["label"] for spec in FIELD_SPECS]
        return [label for label in ordered_labels if label in missing]

    def has_minimum_runnable_info(self, session: TaskSession) -> bool:
        return not self.get_missing_fields(session)

    def checklist_text(self) -> str:
        lines = [
            "\u5df2\u6536\u5230\u9700\u6c42\u3002\u8bf7\u4f18\u5148\u6309\u4ee5\u4e0b\u7814\u7a76\u4efb\u52a1\u4fe1\u606f\u6e05\u5355\u63d0\u4f9b\u4fe1\u606f\uff1a",
            "",
            "\u7814\u7a76\u4efb\u52a1\u4fe1\u606f\u6e05\u5355\uff1a",
        ]
        for spec in FIELD_SPECS:
            lines.append(f"- {spec['label']} ({spec['priority']})")
        lines.append("")
        lines.append(
            "\u4f60\u53ef\u4ee5\u4e00\u6b21\u6027\u53d1\u5b8c\u6574\uff0c\u4e5f\u53ef\u4ee5\u5148\u53d1\u4e00\u90e8\u5206\u3002\u6211\u4f1a\u5148\u6574\u7406\u7f3a\u5931\u9879\uff0c\u518d\u63d0\u9192\u4f60\u8fd0\u884c\u3002"
        )
        return "\n".join(lines)

    def reset_confirmation_text(self) -> str:
        return "\u5df2\u4e3a\u4f60\u6e05\u7a7a\u5f53\u524d\u7fa4\u91cc\u7684\u5f53\u524d\u7814\u7a76\u4efb\u52a1\uff0c\u4f1a\u6309\u65b0\u4efb\u52a1\u91cd\u65b0\u6536\u96c6\u4fe1\u606f\u3002"

    def build_follow_up_text(self, session: TaskSession) -> str:
        known = self.summarize_known_information(session)
        lines = ["\u5df2\u6574\u7406\u5f53\u524d\u7814\u7a76\u4efb\u52a1\u3002"]
        if known:
            lines.append("\u5df2\u63d0\u4f9b\uff1a")
            for label, value in known.items():
                lines.append(f"- {label}\uff1a{value}")

        if session.attachments:
            lines.append("\u5df2\u5904\u7406\u4f60\u4e0a\u4f20\u7684\u56fe\u7247\uff0c\u5e76\u5c1d\u8bd5\u63d0\u53d6\u5173\u952e\u4ea7\u54c1\u4fe1\u606f\u3002\u5982\u6709\u504f\u5dee\uff0c\u53ef\u76f4\u63a5\u56de\u590d\u201c\u4fee\u6b63\uff1a\u5b57\u6bb5=\u5185\u5bb9\u201d\u8fdb\u884c\u8986\u76d6\u3002")

        if session.missing_fields:
            lines.append("\u8fd8\u7f3a\u4ee5\u4e0b\u4fe1\u606f\uff1a")
            for label in session.missing_fields:
                lines.append(f"- {label}")
            if FIELD_LABELS["persona_id"] in session.missing_fields:
                lines.append(
                    "\u8bf7\u6307\u5b9a\u5988\u5988\u753b\u50cf\uff0c\u4f8b\u5982\uff1a\u9ad8\u7ebf\u5fd9\u788c\u5988\u5988 \u6216 M04\u3002"
                )
        else:
            lines.append("\u4fe1\u606f\u5df2\u6536\u9f50\uff0c\u5982\u7ee7\u7eed\u8bf7\u76f4\u63a5\u56de\u590d\u201c\u6309\u5f53\u524d\u4fe1\u606f\u8fd0\u884c\u201d\u3002")
        return "\n".join(lines)

    def build_clarification_text(self, session: TaskSession) -> str:
        plan = session.research_plan or {}
        questions = plan.get("clarifying_questions", [])
        missing = plan.get("missing_information", [])
        lines = ["\u5f53\u524d\u8d44\u6599\u8fd8\u4e0d\u8db3\u4ee5\u53d1\u8d77\u8c03\u7814\uff0c\u8bf7\u5148\u8865\u5145\u4ee5\u4e0b\u4fe1\u606f\uff1a"]
        for item in missing:
            lines.append(f"- {item}")
        if questions:
            lines.append("")
            lines.append("\u5efa\u8bae\u4f60\u8865\u5145\uff1a")
            for item in questions:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def build_readiness_clarification_text(self, readiness_decision: Optional[Dict[str, Any]]) -> str:
        decision = readiness_decision or {}
        reasons = set(decision.get("blocking_reasons", []))

        if "product_context" in reasons or "copy_candidates" in reasons:
            return "\u8bf7\u8865\u5145\u4ea7\u54c1\u4fe1\u606f\u6216\u6838\u5fc3\u5356\u70b9\u3002"
        if "price_range" in reasons or "benchmark_reference" in reasons:
            return "\u8bf7\u8865\u5145\u4ef7\u683c\u533a\u95f4\uff0c\u5e76\u8bf4\u660e\u4ef7\u683c\u6d4b\u8bd5\u65b9\u5f0f\u6216\u5bf9\u6807\u53c2\u8003\u3002"
        if "persona_id" in reasons:
            return "\u8bf7\u6307\u5b9a\u5355\u4eba\u6a21\u5f0f\u4e0b\u8981\u8c03\u7814\u7684\u5988\u5988\u753b\u50cf\u3002"
        if "research_goal" in reasons:
            return "\u8bf7\u8865\u5145\u672c\u6b21\u7814\u7a76\u60f3\u89e3\u51b3\u7684\u6838\u5fc3\u95ee\u9898\u3002"
        return "\u5f53\u524d\u8d44\u6599\u8fd8\u4e0d\u8db3\u4ee5\u53d1\u8d77\u8c03\u7814\uff0c\u8bf7\u5148\u8865\u5145\u5173\u952e\u4fe1\u606f\u3002"

    def summarize_known_information(self, session: TaskSession) -> Dict[str, str]:
        provided = {}
        for field_state in session.fields.values():
            if field_state["status"] == "provided" and field_state["value"] is not None:
                provided[field_state["label"]] = str(field_state["value"])
        return provided

    def build_research_input_payload(
        self,
        session: TaskSession,
        business_brief: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        brief_data = business_brief or session.business_brief
        if not brief_data:
            raise RuntimeError(
                "BusinessBrief is required for research input payload. "
                "Ensure build_business_brief node runs before dispatch."
            )
        from backend.domain.business_brief import BusinessBrief

        brief = BusinessBrief.model_validate(brief_data)
        payload = brief.to_research_input_payload(
            mode=self._field_text(session, "mode"),
            persona_id=self._field_text(session, "persona_id"),
            attachments=list(session.attachments),
            follow_up_context=session.follow_up_context,
            background_material=self._field_text(session, "background_material"),
        )
        # Phase 3: pass research methodology flags
        egd = self._field_text(session, "enable_group_discussion")
        edd = self._field_text(session, "enable_deep_dive")
        payload["enable_group_discussion"] = egd.lower() == "true" if egd else False
        payload["enable_deep_dive"] = edd.lower() == "true" if edd else False
        return payload

    def _field_text(self, session: TaskSession, key: str) -> str:
        value = session.fields[key]["value"]
        return "" if value is None else str(value).strip()

    def _set_if_missing(self, session: TaskSession, key: str, value: Any) -> None:
        text = "" if value is None else str(value).strip()
        if not text:
            return
        if self._field_text(session, key):
            return
        self._set_field_value(session, key, text)

    def _merge_copy_material(self, session: TaskSession, claims: List[str]) -> None:
        normalized_claims = [str(item).strip() for item in claims if str(item).strip()]
        if not normalized_claims:
            return
        existing = self._field_text(session, "copy_material")
        if not existing:
            self._set_field_value(session, "copy_material", "\n".join(normalized_claims))
            return
        merged = list(dict.fromkeys([line.strip() for line in existing.splitlines() if line.strip()] + normalized_claims))
        self._set_field_value(session, "copy_material", "\n".join(merged))

    def _merge_product_info(self, session: TaskSession, lines: List[str]) -> None:
        normalized_lines = [str(line).strip() for line in lines if str(line).strip()]
        if not normalized_lines:
            return
        existing = self._field_text(session, "product_info")
        if not existing:
            self._set_field_value(session, "product_info", "\n".join(normalized_lines))
            return
        existing_lines = [line.strip() for line in existing.splitlines() if line.strip()]
        merged = list(dict.fromkeys(existing_lines + normalized_lines))
        self._set_field_value(session, "product_info", "\n".join(merged))

    def _append_unique_items(self, target: List[str], values: List[str]) -> None:
        for value in values:
            text = str(value).strip()
            if text and text not in target:
                target.append(text)

    def _append_product_context_note(self, session: TaskSession, label: str, value: Any) -> None:
        text = "" if value is None else str(value).strip()
        if not text:
            return
        note = f"{label}: {text}"
        if note not in session.product_context_notes:
            session.product_context_notes.append(note)

    def _extract_source_links(self, text: str) -> List[str]:
        links = []
        for match in SOURCE_LINK_PATTERN.finditer(text or ""):
            link = match.group(0).rstrip(".,;!?)]}")
            if link:
                links.append(link)
        return links

    def _extract_custom_questions(self, text: str) -> List[str]:
        questions = []
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if self._extract_line_field_updates(line):
                continue
            if not any(token in line for token in CUSTOM_QUESTION_HINTS):
                continue
            candidate = SOURCE_LINK_PATTERN.sub("", line).strip()
            if candidate:
                questions.append(candidate)
        return questions

    def _apply_attachment_enrichment(self, session: TaskSession, attachments: List[str]) -> None:
        if not attachments or self.ai_client is None:
            return

        for attachment in attachments:
            try:
                from pathlib import Path as _Path

                attachment_path = _Path(attachment)
                if not attachment_path.exists() or not attachment_path.is_file():
                    continue
                if attachment_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    continue

                extracted = self.ai_client.extract_product_fields_from_image(attachment_path)
                fields = extracted.get("fields", {}) if isinstance(extracted, dict) else {}
                if not isinstance(fields, dict) or not fields:
                    continue

                concept_name = str(fields.get("concept_name", "")).strip()
                category = str(fields.get("category", "")).strip()
                price = str(fields.get("price", "")).strip()
                pack_summary = str(fields.get("packaging_summary", "")).strip()
                detail_copy = str(fields.get("detail_copy", "")).strip()
                slogan = str(fields.get("slogan", "")).strip()
                target_audience = str(fields.get("target_audience", "")).strip()
                brand = str(fields.get("brand", "")).strip()
                channels = fields.get("target_channels", []) if isinstance(fields.get("target_channels"), list) else []
                claims = fields.get("core_claims", []) if isinstance(fields.get("core_claims"), list) else []

                product_lines: List[str] = []
                if concept_name:
                    product_lines.append(f"概念名: {concept_name}")
                if category:
                    product_lines.append(f"品类: {category}")
                if price:
                    product_lines.append(f"价格: {price}")
                if pack_summary:
                    product_lines.append(f"包装与主信息: {pack_summary}")
                if detail_copy:
                    product_lines.append(f"详情文案: {detail_copy[:400]}")

                if product_lines:
                    self._merge_product_info(session, product_lines)
                if slogan:
                    self._merge_copy_material(session, [slogan])
                if claims:
                    self._merge_copy_material(session, [str(c) for c in claims])

                self._set_if_missing(session, "brand", brand)
                if channels:
                    self._set_if_missing(session, "channel", str(channels[0]))
                if target_audience:
                    self._set_if_missing(session, "target_age", target_audience)
            except Exception as exc:
                logger.warning("Attachment OCR enrichment failed for %s: %s", attachment, exc)

    def _apply_attachment_enrichment_v2(self, session: TaskSession, attachments: List[str]) -> None:
        if not attachments or self.ai_client is None:
            return

        extractor = getattr(self.ai_client, "extract_product_fields_from_image", None)
        if not callable(extractor):
            return

        for attachment in attachments:
            try:
                attachment_path = Path(attachment)
                if not attachment_path.exists() or not attachment_path.is_file():
                    continue
                if attachment_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    continue

                extracted = extractor(attachment_path)
                fields = extracted.get("fields", {}) if isinstance(extracted, dict) else {}
                if not isinstance(fields, dict) or not fields:
                    continue

                concept_name = str(fields.get("concept_name", "")).strip()
                category = str(fields.get("category", "")).strip()
                price = str(fields.get("price", "")).strip()
                pack_summary = str(fields.get("packaging_summary", "")).strip()
                detail_copy = str(fields.get("detail_copy", "")).strip()
                slogan = str(fields.get("slogan", "")).strip()
                target_audience = str(fields.get("target_audience", "")).strip()
                brand = str(fields.get("brand", "")).strip()
                channels = fields.get("target_channels", []) if isinstance(fields.get("target_channels"), list) else []
                claims = fields.get("core_claims", []) if isinstance(fields.get("core_claims"), list) else []

                self._append_product_context_note(session, "concept_name", concept_name)
                self._append_product_context_note(session, "category", category)
                self._append_product_context_note(session, "brand", brand)
                self._append_product_context_note(session, "price", price)
                self._append_product_context_note(session, "packaging_summary", pack_summary)
                self._append_product_context_note(session, "detail_copy", detail_copy[:400] if detail_copy else "")
                self._append_product_context_note(session, "slogan", slogan)
                if claims:
                    self._append_product_context_note(
                        session,
                        "core_claims",
                        "; ".join(str(c).strip() for c in claims if str(c).strip()),
                    )
                self._append_product_context_note(
                    session,
                    "ocr_text",
                    extracted.get("raw_text") if isinstance(extracted, dict) else "",
                )

                self._set_if_missing(session, "product_info", concept_name)
                if not self._field_text(session, "copy_material"):
                    self._set_if_missing(
                        session,
                        "copy_material",
                        detail_copy or "\n".join(str(c).strip() for c in claims if str(c).strip()) or slogan,
                    )

                self._set_if_missing(session, "brand", brand)
                if channels:
                    self._set_if_missing(session, "channel", str(channels[0]))
                if target_audience:
                    self._set_if_missing(session, "target_age", target_audience)
            except Exception as exc:
                logger.warning("Attachment OCR enrichment failed for %s: %s", attachment, exc)

    def _normalize_status(self, status: str) -> str:
        mapping = {
            "collecting": "intake",
            "normalizing": "normalizing",
            "awaiting_clarification": "awaiting_clarification",
            "awaiting_run_confirmation": "awaiting_authorization",
            "awaiting_authorization": "awaiting_authorization",
            "planning": "ready_to_dispatch",
            "ready_to_dispatch": "ready_to_dispatch",
            "running": "dispatching",
            "dispatching": "dispatching",
            "summarizing": "summarizing",
            "completed": "completed",
            "error": "recovery",
            "recovery": "recovery",
            "expired": "expired",
        }
        return mapping.get((status or "").strip(), (status or "").strip())

    def _validate_status_transition(self, previous_status: str, next_status: str) -> None:
        previous = self._normalize_status(previous_status)
        current = self._normalize_status(next_status)
        if not previous or not current or previous == current:
            return

        allowed = {
            "intake": {"normalizing", "awaiting_clarification", "awaiting_authorization", "ready_to_dispatch", "dispatching", "recovery", "expired"},
            "normalizing": {"intake", "awaiting_clarification", "awaiting_authorization", "ready_to_dispatch", "recovery", "expired"},
            "awaiting_clarification": {"intake", "awaiting_clarification", "normalizing", "ready_to_dispatch", "recovery", "expired"},
            "awaiting_authorization": {"intake", "awaiting_authorization", "ready_to_dispatch", "normalizing", "recovery", "expired"},
            "ready_to_dispatch": {"dispatching", "normalizing", "recovery", "expired"},
            "dispatching": {"dispatching", "awaiting_clarification", "summarizing", "completed", "recovery"},
            "summarizing": {"summarizing", "completed", "recovery"},
            "completed": {"intake", "normalizing", "completed"},
            "recovery": {"normalizing", "awaiting_clarification", "awaiting_authorization", "ready_to_dispatch", "recovery", "expired"},
            "expired": {"normalizing", "expired"},
        }
        if current not in allowed.get(previous, set()):
            raise ValueError(f"Invalid session status transition: {previous_status} -> {next_status}")

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
        lowered = (text or "").lower()
        for alias, normalized in MODE_ALIASES.items():
            if alias.lower() in lowered:
                return normalized
        return ""

    def infer_question_type(self, text: str) -> str:
        normalized = (text or "").strip()
        lowered = normalized.lower()
        for alias, mapped in QUESTION_TYPE_ALIASES.items():
            if alias.lower() in lowered:
                return mapped
        if any(token in lowered for token in ["a/b", "ab test", "ab\u6d4b\u8bd5"]) or "ab\u7248" in normalized:
            return "ab_test"
        if any(token in normalized for token in ["\u4ef7\u683c\u6d4b\u8bd5", "\u4ef7\u683c\u654f\u611f", "\u5b9a\u4ef7", "\u6d4b\u4ef7"]):
            return "price_test"
        if "\u6587\u6848" in normalized or "\u5356\u70b9" in normalized:
            return "copy_feedback"
        if any(token in normalized for token in ["\u75db\u70b9", "\u600e\u4e48\u89e3\u51b3", "\u7f3a\u5c11\u4ec0\u4e48"]):
            return "needs_pain_points"
        if any(token in normalized for token in ["\u4f1a\u4e0d\u4f1a\u4e70", "\u4e3a\u4ec0\u4e48\u4e70", "\u6700\u5927\u987e\u8651", "\u8d2d\u4e70\u51b3\u7b56"]):
            return "purchase_decision"
        if any(token in normalized for token in ["\u6982\u5ff5", "\u5438\u5f15\u529b", "\u611f\u5174\u8da3"]):
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
        if "\u5988\u5988\u5b9a\u6027\u7814\u7a76" in text and len(text) <= 20:
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

        if matches and matches[0][0] == "question_type":
            matches = [matches[0]]

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
            normalized_value = MODE_ALIASES.get(str(value), MODE_ALIASES.get(str(value).lower(), value))
        elif key == "question_type":
            normalized_value = QUESTION_TYPE_ALIASES.get(
                str(value),
                QUESTION_TYPE_ALIASES.get(str(value).lower(), self.infer_question_type(str(value)) or value),
            )
        elif key == "persona_id":
            normalized_value = self.persona_alias_map.get(str(value), value)
        elif key == "price_test_mode":
            normalized_value = PRICE_TEST_MODE_ALIASES.get(
                str(value),
                PRICE_TEST_MODE_ALIASES.get(str(value).lower(), value),
            )
        elif key == "price_anchor_type":
            normalized_value = PRICE_ANCHOR_ALIASES.get(
                str(value),
                PRICE_ANCHOR_ALIASES.get(str(value).lower(), value),
            )

        state = session.fields[key]
        state["status"] = "provided"
        state["value"] = str(normalized_value).strip()

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
        from backend.infra.privacy_utils import hash_identifier

        return "__".join(
            [
                hash_identifier(group_id),
                hash_identifier(conversation_id),
                hash_identifier(user_id),
            ]
        )

    def _path_for(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"

    def _default_retention_policy(self) -> Dict[str, Any]:
        from backend.infra.privacy_utils import build_retention_policy

        return build_retention_policy()

    def _serialize_for_storage(self, session: TaskSession) -> Dict[str, Any]:
        from backend.infra.privacy_utils import hash_identifier

        payload = session.to_dict()
        payload["group_id"] = hash_identifier(str(payload["group_id"]))
        payload["conversation_id"] = hash_identifier(str(payload["conversation_id"]))
        payload["user_id"] = hash_identifier(str(payload["user_id"]))
        if payload.get("authorization_requested_by"):
            payload["authorization_requested_by"] = hash_identifier(str(payload["authorization_requested_by"]))
        payload["retention_policy"] = session.retention_policy or self._default_retention_policy()
        payload["identifiers_hashed"] = True
        return payload

    def _snapshot_payload(self, session: TaskSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "status": session.status,
            "business_brief": session.business_brief,
            "readiness_decision": session.readiness_decision,
            "retention_policy": session.retention_policy or self._default_retention_policy(),
            "payload": payload,
        }
