import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List


SUMMARY_KEYS = [
    "consensus",
    "differences",
    "pain_points",
    "drivers",
    "barriers",
    "copy_insights",
    "recommendations",
]

PLANNER_REQUIRED_KEYS = [
    "normalized_intent",
    "question_type",
    "recommended_mode",
    "target_persona",
    "research_objectives",
    "evaluation_dimensions",
    "required_materials",
    "missing_information",
    "clarification_questions",
    "assumptions_if_run_now",
    "is_runnable",
    "needs_clarification",
]

MOM_REQUIRED_KEYS = [
    "persona_id",
    "persona_name",
    "stance",
    "core_needs",
    "motivations",
    "concerns",
    "decision_logic",
    "verbatim_answer",
    "evidence_trace",
]

MOM_PERSONA_FIELDS = [
    "segment_id",
    "segment_name",
    "sample_id",
    "basic_profile",
    "mindset_profile",
    "consumption_profile",
    "expression_profile",
    "review_focus",
]

QUESTION_TYPE_VALUES = {
    "product_concept",
    "purchase_decision",
    "needs_pain_points",
    "copy_feedback",
}

MODE_VALUES = {"multi", "single"}

NUMERIC_TOKEN_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)[\s\u00A0]*(个月|小时|分钟|毫升|厘米|kg|KG|cm|CM|ml|ML|g|G|%|％|次|天|年|月|周|元|岁|支|件|袋|片|滴)"
)


@dataclass
class QualitativeResearchInput:
    mode: str
    question_type: str
    user_question: str
    persona_id: str = ""
    background_material: str = ""
    product_info: str = ""
    copy_material: str = ""
    attachments: List[str] = field(default_factory=list)
    follow_up_context: str = ""
    allow_assumption_run: bool = False
    planner_result: Dict[str, Any] = field(default_factory=dict)


class IncompleteResearchRunError(RuntimeError):
    pass


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}

    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _normalize_string_list(value: Any, key: str, allow_empty: bool = False) -> List[str]:
    if not isinstance(value, list):
        raise IncompleteResearchRunError(f"{key} must be a list.")

    items = [str(item).strip() for item in value if str(item).strip()]
    if not items and not allow_empty:
        raise IncompleteResearchRunError(f"{key} cannot be empty.")
    return items


def _normalize_string(value: Any, key: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise IncompleteResearchRunError(f"{key} cannot be empty.")
    return text


def _normalize_optional_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise IncompleteResearchRunError(f"{key} must be a boolean.")
    return value


def _extract_numeric_tokens(text: str) -> List[tuple[str, str]]:
    if not text:
        return []
    return [(match.group(1), f"{match.group(1)}{match.group(2)}") for match in NUMERIC_TOKEN_PATTERN.finditer(text)]


def _persona_prompt_payload(persona: Dict[str, Any]) -> Dict[str, Any]:
    return {key: persona.get(key) for key in MOM_PERSONA_FIELDS}


class ResearchPlannerAgent:
    def __init__(self, ai_client: Any):
        self.ai_client = ai_client

    def run(self, research_input: QualitativeResearchInput) -> Dict[str, Any]:
        result = self.ai_client.generate_text(
            prompt=self._build_prompt(research_input),
            system_prompt=(
                "You are a qualitative research planner. "
                "Identify the user intent, decompose the task, detect missing information, "
                "and return strict JSON only."
            ),
        )
        if result.get("mode") != "live_text":
            raise IncompleteResearchRunError("Research planner did not complete with a live LLM response.")

        payload = _extract_json_object(result.get("text", ""))
        if not payload:
            raise IncompleteResearchRunError("Research planner returned invalid JSON.")
        return self._validate_payload(payload)

    def _build_prompt(self, research_input: QualitativeResearchInput) -> str:
        return "\n".join(
            [
                "Decompose the qualitative research request below before any consumer interviews happen.",
                "Write in Simplified Chinese for all list items and text fields.",
                "Do not invent missing facts as if they were confirmed.",
                "If key information is missing, set needs_clarification to true and provide concrete clarification_questions.",
                "Only mark is_runnable true when the current brief is sufficient for a defensible research run.",
                "Return strict JSON only with this schema:",
                json.dumps(
                    {
                        "normalized_intent": "one concise sentence",
                        "question_type": "product_concept|purchase_decision|needs_pain_points|copy_feedback",
                        "recommended_mode": "multi|single",
                        "target_persona": "persona id or alias if clearly implied, else empty string",
                        "research_objectives": ["objective 1", "objective 2"],
                        "evaluation_dimensions": ["dimension 1", "dimension 2"],
                        "required_materials": ["material 1", "material 2"],
                        "missing_information": ["missing item 1"],
                        "clarification_questions": ["question 1"],
                        "assumptions_if_run_now": ["assumption 1"],
                        "is_runnable": False,
                        "needs_clarification": True,
                    },
                    ensure_ascii=False,
                ),
                "",
                "Current brief:",
                json.dumps(
                    {
                        "mode": research_input.mode,
                        "question_type": research_input.question_type,
                        "persona_id": research_input.persona_id,
                        "user_question": research_input.user_question,
                        "background_material": research_input.background_material,
                        "product_info": research_input.product_info,
                        "copy_material": research_input.copy_material,
                        "follow_up_context": research_input.follow_up_context,
                        "allow_assumption_run": research_input.allow_assumption_run,
                    },
                    ensure_ascii=False,
                ),
            ]
        )

    def _validate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        for key in PLANNER_REQUIRED_KEYS:
            if key not in payload:
                raise IncompleteResearchRunError(f"Research planner payload missing {key}.")

        question_type = _normalize_string(payload.get("question_type"), "question_type")
        if question_type not in QUESTION_TYPE_VALUES:
            raise IncompleteResearchRunError(f"Research planner returned unsupported question_type {question_type}.")

        recommended_mode = _normalize_string(payload.get("recommended_mode"), "recommended_mode")
        if recommended_mode not in MODE_VALUES:
            raise IncompleteResearchRunError(f"Research planner returned unsupported recommended_mode {recommended_mode}.")

        needs_clarification = _normalize_bool(payload.get("needs_clarification"), "needs_clarification")
        clarification_questions = _normalize_string_list(
            payload.get("clarification_questions"),
            "clarification_questions",
            allow_empty=not needs_clarification,
        )

        normalized = {
            "normalized_intent": _normalize_string(payload.get("normalized_intent"), "normalized_intent"),
            "question_type": question_type,
            "recommended_mode": recommended_mode,
            "target_persona": _normalize_optional_string(payload.get("target_persona")),
            "research_objectives": _normalize_string_list(payload.get("research_objectives"), "research_objectives"),
            "evaluation_dimensions": _normalize_string_list(
                payload.get("evaluation_dimensions"),
                "evaluation_dimensions",
            ),
            "required_materials": _normalize_string_list(payload.get("required_materials"), "required_materials"),
            "missing_information": _normalize_string_list(
                payload.get("missing_information"),
                "missing_information",
                allow_empty=True,
            ),
            "clarification_questions": clarification_questions,
            "assumptions_if_run_now": _normalize_string_list(
                payload.get("assumptions_if_run_now"),
                "assumptions_if_run_now",
                allow_empty=True,
            ),
            "is_runnable": _normalize_bool(payload.get("is_runnable"), "is_runnable"),
            "needs_clarification": needs_clarification,
        }
        return normalized


class MomPersonaAgent:
    def __init__(self, persona: Dict[str, Any], ai_client: Any):
        self.persona = persona
        self.ai_client = ai_client

    def run(self, research_input: QualitativeResearchInput, research_plan: Dict[str, Any] | None = None) -> Dict[str, Any]:
        self._active_user_question = research_input.user_question
        self._active_copy_material = research_input.copy_material
        self._active_product_info = research_input.product_info
        self._active_background_material = research_input.background_material
        result = self.ai_client.generate_text(
            prompt=self._build_prompt(research_input, research_plan=research_plan),
            system_prompt=(
                "You are speaking as one specific Chinese mother consumer persona. "
                "Return strict JSON only and do not include markdown."
            ),
        )
        if result.get("mode") != "live_text":
            raise IncompleteResearchRunError("Mother agent did not complete with a live LLM response.")

        payload = _extract_json_object(result.get("text", ""))
        if not payload:
            raise IncompleteResearchRunError("Mother agent returned invalid JSON.")
        return self._validate_payload(payload, research_input.question_type)

    def _build_prompt(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any] | None = None,
    ) -> str:
        return "\n".join(
            [
                "Role-play exactly one mother persona based on the profile below.",
                "Write as the consumer herself, not as an analyst.",
                "Write in Simplified Chinese.",
                "Keep the output concise.",
                "Do not change any key numbers, durations, frequencies, prices, or claim wording from the brief.",
                "Use at most 2 items for each list.",
                "Keep decision_logic under 40 Chinese characters.",
                "Keep verbatim_answer under 90 Chinese characters.",
                "Keep evidence_trace under 60 Chinese characters.",
                "Return strict JSON only with this schema:",
                json.dumps(
                    {
                        "persona_id": "segment id",
                        "persona_name": "display name",
                        "stance": "interested|hesitant|rejecting",
                        "core_needs": ["need 1", "need 2"],
                        "motivations": ["motivation 1", "motivation 2"],
                        "concerns": ["concern 1", "concern 2"],
                        "decision_logic": "one short sentence",
                        "verbatim_answer": "one consumer-sounding answer in Chinese",
                        "evidence_trace": "brief note describing why this persona answered that way",
                    },
                    ensure_ascii=False,
                ),
                "",
                "Persona profile:",
                json.dumps(_persona_prompt_payload(self.persona), ensure_ascii=False),
                "",
                "Research brief:",
                json.dumps(
                    {
                        "mode": research_input.mode,
                        "question_type": research_input.question_type,
                        "user_question": research_input.user_question,
                        "persona_id": research_input.persona_id,
                        "background_material": research_input.background_material,
                        "product_info": research_input.product_info,
                        "copy_material": research_input.copy_material,
                        "follow_up_context": research_input.follow_up_context,
                    },
                    ensure_ascii=False,
                ),
                "",
                "Research plan:",
                json.dumps(research_plan or {}, ensure_ascii=False),
            ]
        )

    def _validate_payload(self, payload: Dict[str, Any], question_type: str) -> Dict[str, Any]:
        for key in MOM_REQUIRED_KEYS:
            if key not in payload:
                raise IncompleteResearchRunError(f"Mother agent payload missing {key}.")

        persona_id = _normalize_string(payload.get("persona_id"), "persona_id")
        expected_persona_id = str(self.persona["segment_id"])
        if persona_id != expected_persona_id:
            raise IncompleteResearchRunError(
                f"Mother agent returned persona_id {persona_id}, expected {expected_persona_id}."
            )

        normalized = {
            "persona_id": persona_id,
            "persona_name": _normalize_string(payload.get("persona_name"), "persona_name"),
            "question_type": question_type,
            "stance": _normalize_string(payload.get("stance"), "stance"),
            "core_needs": _normalize_string_list(payload.get("core_needs"), "core_needs"),
            "motivations": _normalize_string_list(payload.get("motivations"), "motivations"),
            "concerns": _normalize_string_list(payload.get("concerns"), "concerns"),
            "decision_logic": _normalize_string(payload.get("decision_logic"), "decision_logic"),
            "verbatim_answer": _normalize_string(payload.get("verbatim_answer"), "verbatim_answer"),
            "evidence_trace": _normalize_string(payload.get("evidence_trace"), "evidence_trace"),
        }
        self._validate_numeric_grounding(normalized)
        return normalized

    def _validate_numeric_grounding(self, payload: Dict[str, Any]) -> None:
        allowed_tokens_by_number: Dict[str, set[str]] = {}
        for source_text in (
            self.persona.get("segment_name", ""),
            payload.get("question_type", ""),
        ):
            for number, token in _extract_numeric_tokens(str(source_text)):
                allowed_tokens_by_number.setdefault(number, set()).add(token)

        # Use only the active brief content as the grounding source for numeric claims.
        for source_text in (
            getattr(self, "_active_user_question", ""),
            getattr(self, "_active_copy_material", ""),
            getattr(self, "_active_product_info", ""),
            getattr(self, "_active_background_material", ""),
        ):
            for number, token in _extract_numeric_tokens(str(source_text)):
                allowed_tokens_by_number.setdefault(number, set()).add(token)

        if not allowed_tokens_by_number:
            return

        for output_text in (
            payload["decision_logic"],
            payload["verbatim_answer"],
            payload["evidence_trace"],
        ):
            for number, token in _extract_numeric_tokens(output_text):
                allowed_for_number = allowed_tokens_by_number.get(number)
                if allowed_for_number and token not in allowed_for_number:
                    raise IncompleteResearchRunError(
                        f"Mother agent introduced conflicting numeric claim {token} for number {number}."
                    )


class ResearchAssistantAgent:
    def __init__(self, ai_client: Any):
        self.ai_client = ai_client

    def run(
        self,
        research_input: QualitativeResearchInput,
        consumer_voice: List[Dict[str, Any]],
        research_plan: Dict[str, Any] | None = None,
    ) -> Dict[str, List[str]]:
        result = self.ai_client.generate_text(
            prompt=self._build_prompt(research_input, consumer_voice, research_plan=research_plan),
            system_prompt=(
                "You are a qualitative research assistant. "
                "Use the brief for context, but ground your conclusions mainly in the mother responses. "
                "Return strict JSON only and do not include markdown."
            ),
        )
        if result.get("mode") != "live_text":
            raise IncompleteResearchRunError("Research assistant did not complete with a live LLM response.")

        payload = _extract_json_object(result.get("text", ""))
        if not payload:
            raise IncompleteResearchRunError("Research assistant returned invalid JSON.")
        return self._validate_payload(payload)

    def _build_prompt(
        self,
        research_input: QualitativeResearchInput,
        consumer_voice: List[Dict[str, Any]],
        research_plan: Dict[str, Any] | None = None,
    ) -> str:
        extra_rules = [
            "Every output list must contain at least one concise item.",
            "Do not leave consensus or differences empty.",
            "Keep each item short and concrete.",
        ]
        if research_input.mode == "single":
            extra_rules.extend(
                [
                    "This is single mode based on one mother persona only.",
                    "In single mode, consensus and differences must explicitly state that they are based on one persona and do not represent group consensus.",
                ]
            )

        return "\n".join(
            [
                "Summarize the qualitative responses below.",
                "You may use the original brief for context, but your reasons should mainly come from the mother responses.",
                "Write every item in Simplified Chinese.",
                *extra_rules,
                "Return strict JSON only with these keys:",
                json.dumps(
                    {
                        "consensus": ["..."],
                        "differences": ["..."],
                        "pain_points": ["..."],
                        "drivers": ["..."],
                        "barriers": ["..."],
                        "copy_insights": ["..."],
                        "recommendations": ["..."],
                    },
                    ensure_ascii=False,
                ),
                "",
                "Research brief:",
                json.dumps(
                    {
                        "mode": research_input.mode,
                        "question_type": research_input.question_type,
                        "user_question": research_input.user_question,
                        "persona_id": research_input.persona_id,
                        "background_material": research_input.background_material,
                        "product_info": research_input.product_info,
                        "copy_material": research_input.copy_material,
                        "follow_up_context": research_input.follow_up_context,
                    },
                    ensure_ascii=False,
                ),
                "",
                "Research plan:",
                json.dumps(research_plan or {}, ensure_ascii=False),
                "",
                "Mother responses:",
                json.dumps(consumer_voice, ensure_ascii=False),
            ]
        )

    def _validate_payload(self, payload: Dict[str, Any]) -> Dict[str, List[str]]:
        normalized: Dict[str, List[str]] = {}
        for key in SUMMARY_KEYS:
            if key not in payload:
                raise IncompleteResearchRunError(f"Research assistant payload missing {key}.")
            normalized[key] = _normalize_string_list(payload.get(key), key)
        return normalized


class QualitativeResearchRunner:
    def __init__(self, persona_path: Path | str, ai_client: Any | None = None):
        self.persona_path = Path(persona_path)
        self.ai_client = ai_client
        self.personas = self._load_personas()

    def run(self, research_input: QualitativeResearchInput) -> Dict[str, Any]:
        self._require_live_ai_client()
        research_plan = self.plan(research_input)
        effective_input = self._apply_research_plan(research_input, research_plan)

        if research_plan["needs_clarification"] and not effective_input.allow_assumption_run:
            return self._build_clarification_report(effective_input, research_plan)

        selected_personas = self._select_personas(effective_input)
        consumer_voice = self._run_mom_agents(selected_personas, effective_input, research_plan=research_plan)

        assistant = ResearchAssistantAgent(self.ai_client)
        summary = assistant.run(effective_input, consumer_voice, research_plan=research_plan)
        assumption_run = bool(research_plan["needs_clarification"] and effective_input.allow_assumption_run)

        return {
            "meta": {
                "mode": effective_input.mode,
                "question_type": effective_input.question_type,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_agents": len(consumer_voice),
                "agent_count_expected": len(selected_personas),
                "agent_count_completed": len(consumer_voice),
                "planner_status": "complete",
                "assumption_run": assumption_run,
                "completion_status": "complete",
            },
            "research_brief": {
                "user_question": effective_input.user_question,
                "product_info": effective_input.product_info,
                "copy_material": effective_input.copy_material,
                "background_material": effective_input.background_material,
            },
            "research_plan": research_plan,
            "consumer_voice": consumer_voice,
            "research_summary": summary,
            "appendix": {
                "selected_persona": effective_input.persona_id or None,
                "follow_up_context": effective_input.follow_up_context,
                "attachments": list(effective_input.attachments),
            },
        }

    def _require_live_ai_client(self) -> None:
        if self.ai_client is None or not getattr(self.ai_client, "is_configured", False):
            raise IncompleteResearchRunError("Qualitative research requires a configured live AI client.")

    def plan(self, research_input: QualitativeResearchInput) -> Dict[str, Any]:
        planner = ResearchPlannerAgent(self.ai_client)
        if research_input.planner_result:
            return planner._validate_payload(dict(research_input.planner_result))
        return planner.run(research_input)

    def _load_personas(self) -> List[Dict[str, Any]]:
        payload = json.loads(self.persona_path.read_text(encoding="utf-8"))
        samples = payload.get("samples", [])
        representatives: Dict[str, Dict[str, Any]] = {}
        for sample in samples:
            representatives.setdefault(sample["segment_id"], sample)
        return [representatives[key] for key in sorted(representatives)]

    def _run_mom_agents(
        self,
        selected_personas: List[Dict[str, Any]],
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        if len(selected_personas) <= 1 or not getattr(self.ai_client, "supports_parallel_calls", False):
            return [
                MomPersonaAgent(persona, self.ai_client).run(research_input, research_plan=research_plan)
                for persona in selected_personas
            ]

        max_workers = min(len(selected_personas), 8)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(MomPersonaAgent(persona, self.ai_client).run, research_input, research_plan)
                for persona in selected_personas
            ]
            return [future.result() for future in futures]

    def _select_personas(self, research_input: QualitativeResearchInput) -> List[Dict[str, Any]]:
        if research_input.mode == "single":
            for persona in self.personas:
                if research_input.persona_id in {persona["segment_id"], persona["sample_id"]}:
                    return [persona]
            raise IncompleteResearchRunError(f"Unknown persona_id: {research_input.persona_id}")
        return list(self.personas)

    def _apply_research_plan(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> QualitativeResearchInput:
        next_mode = research_plan.get("recommended_mode") or research_input.mode
        next_question_type = research_plan.get("question_type") or research_input.question_type
        next_persona_id = research_input.persona_id
        if next_mode == "single" and research_plan.get("target_persona"):
            next_persona_id = research_plan["target_persona"]

        return replace(
            research_input,
            mode=next_mode,
            question_type=next_question_type,
            persona_id=next_persona_id,
        )

    def _build_clarification_report(
        self,
        research_input: QualitativeResearchInput,
        research_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "meta": {
                "mode": research_input.mode,
                "question_type": research_plan["question_type"],
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_agents": 0,
                "agent_count_expected": 0,
                "agent_count_completed": 0,
                "planner_status": "complete",
                "assumption_run": False,
                "completion_status": "clarification_required",
            },
            "research_brief": {
                "user_question": research_input.user_question,
                "product_info": research_input.product_info,
                "copy_material": research_input.copy_material,
                "background_material": research_input.background_material,
            },
            "research_plan": research_plan,
            "consumer_voice": [],
            "research_summary": {},
            "appendix": {
                "selected_persona": research_input.persona_id or research_plan.get("target_persona") or None,
                "follow_up_context": research_input.follow_up_context,
                "attachments": list(research_input.attachments),
            },
        }
