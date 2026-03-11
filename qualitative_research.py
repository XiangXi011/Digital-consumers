import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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


class QualitativeResearchRunner:
    def __init__(self, persona_path: Path | str, ai_client: Any | None = None):
        self.persona_path = Path(persona_path)
        self.ai_client = ai_client
        self.personas = self._load_personas()

    def run(self, research_input: QualitativeResearchInput) -> Dict[str, Any]:
        selected_personas = self._select_personas(research_input)
        consumer_voice = [
            self._build_persona_response(persona, research_input)
            for persona in selected_personas
        ]
        summary = self._build_summary(consumer_voice, research_input)
        return {
            "meta": {
                "mode": research_input.mode,
                "question_type": research_input.question_type,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_agents": len(consumer_voice),
            },
            "research_brief": {
                "user_question": research_input.user_question,
                "product_info": research_input.product_info,
                "copy_material": research_input.copy_material,
                "background_material": research_input.background_material,
            },
            "consumer_voice": consumer_voice,
            "research_summary": summary,
            "appendix": {
                "selected_persona": research_input.persona_id or None,
                "follow_up_context": research_input.follow_up_context,
                "attachments": list(research_input.attachments),
            },
        }

    def _load_personas(self) -> List[Dict[str, Any]]:
        payload = json.loads(self.persona_path.read_text(encoding="utf-8"))
        samples = payload.get("samples", [])
        representatives: Dict[str, Dict[str, Any]] = {}
        for sample in samples:
            representatives.setdefault(sample["segment_id"], sample)
        return [representatives[key] for key in sorted(representatives)]

    def _select_personas(self, research_input: QualitativeResearchInput) -> List[Dict[str, Any]]:
        if research_input.mode == "single":
            for persona in self.personas:
                if research_input.persona_id in {persona["segment_id"], persona["sample_id"]}:
                    return [persona]
            raise ValueError(f"Unknown persona_id: {research_input.persona_id}")
        return list(self.personas)

    def _build_persona_response(
        self,
        persona: Dict[str, Any],
        research_input: QualitativeResearchInput,
    ) -> Dict[str, Any]:
        nickname = persona["basic_profile"]["nickname"]
        segment_name = persona["segment_name"]
        likely_quote = persona["expression_profile"].get("likely_quote", "")
        core_needs = list(persona["consumption_profile"].get("core_needs", []))[:2]
        trust_trigger = persona["consumption_profile"].get("trust_trigger", "")
        rejection_trigger = persona["consumption_profile"].get("rejection_trigger", "")
        review_focus = list(persona.get("review_focus", []))[:2]
        stance = self._derive_stance(persona, research_input.question_type)
        motivations = [item for item in [trust_trigger, *review_focus] if item][:2]
        concerns = [item for item in [rejection_trigger, self._question_specific_concern(research_input)] if item][:2]

        return {
            "persona_id": persona["segment_id"],
            "persona_name": nickname,
            "question_type": research_input.question_type,
            "stance": stance,
            "core_needs": core_needs,
            "motivations": motivations,
            "concerns": concerns,
            "decision_logic": (
                f"{segment_name}这类妈妈会先看{trust_trigger or '核心证据'}，"
                f"再结合{persona['mindset_profile'].get('decision_mode', '自己的经验')}做判断。"
            ),
            "verbatim_answer": self._build_verbatim_answer(
                nickname=nickname,
                likely_quote=likely_quote,
                stance=stance,
                research_input=research_input,
                concerns=concerns,
            ),
            "confidence_note": "基于现有妈妈画像和当前提供信息生成。",
        }

    def _derive_stance(self, persona: Dict[str, Any], question_type: str) -> str:
        purchase_decision = persona.get("purchase_decision", "")
        rating = persona.get("product_rating", 0)
        if question_type == "purchase_decision":
            if "不" in purchase_decision:
                return "rejecting"
            if "持续" in purchase_decision or "回购" in purchase_decision:
                return "interested"
            return "hesitant"
        if rating >= 8:
            return "interested"
        if rating >= 6:
            return "hesitant"
        return "rejecting"

    def _question_specific_concern(self, research_input: QualitativeResearchInput) -> str:
        mapping = {
            "product_concept": "还想先确认这个概念不是噱头。",
            "purchase_decision": "要再确认值不值得买。",
            "needs_pain_points": "现有方案能不能真的解决问题。",
            "copy_feedback": "表达是不是足够清楚可信。",
        }
        return mapping.get(research_input.question_type, "还需要更多信息判断。")

    def _build_verbatim_answer(
        self,
        nickname: str,
        likely_quote: str,
        stance: str,
        research_input: QualitativeResearchInput,
        concerns: List[str],
    ) -> str:
        stance_opening = {
            "interested": "我会愿意继续了解，",
            "hesitant": "我会先放进备选，",
            "rejecting": "我暂时不会马上买，",
        }[stance]
        material_hint = research_input.copy_material or research_input.product_info or research_input.user_question
        concern_text = concerns[0] if concerns else "我还想再看看。"
        if likely_quote:
            return (
                f"{likely_quote}。{stance_opening}"
                f"但前提是你得把“{material_hint[:24]}”这件事讲明白，"
                f"不然我会觉得{concern_text}"
            )
        return (
            f"我是{nickname}这类妈妈，{stance_opening}"
            f"现在最关键的是“{material_hint[:24]}”，"
            f"否则我会觉得{concern_text}"
        )

    def _build_summary(
        self,
        consumer_voice: List[Dict[str, Any]],
        research_input: QualitativeResearchInput,
    ) -> Dict[str, List[str]]:
        needs = self._top_items(consumer_voice, "core_needs")
        motivations = self._top_items(consumer_voice, "motivations")
        concerns = self._top_items(consumer_voice, "concerns")
        interested = [item["persona_name"] for item in consumer_voice if item["stance"] == "interested"]
        rejecting = [item["persona_name"] for item in consumer_voice if item["stance"] == "rejecting"]

        if research_input.mode == "single":
            differences = ["当前仅基于单一妈妈画像输出，不代表群体分歧。"]
            consensus = ["当前仅基于单一妈妈画像输出，不代表群体共识。"]
        else:
            differences = [
                f"更容易被打动的妈妈有：{'、'.join(interested[:3]) or '暂无明显支持者'}。",
                f"保留或拒绝更多的妈妈有：{'、'.join(rejecting[:3]) or '暂无明显拒绝者'}。",
            ]
            consensus = [
                f"多数妈妈都会先看：{needs[0] if needs else '核心需求是否被正面回应'}。",
                f"大家普遍都会追问：{concerns[0] if concerns else '信息是否足够可信'}。",
            ]

        copy_hint = research_input.copy_material or research_input.product_info or research_input.user_question
        summary = {
            "consensus": consensus,
            "differences": differences,
            "pain_points": [
                f"当前最明显的痛点集中在：{needs[0] if needs else '真实场景需求未被直接击中'}。",
            ],
            "drivers": [
                f"主要购买驱动来自：{motivations[0] if motivations else '被清楚证明的核心利益点'}。",
            ],
            "barriers": [
                f"核心障碍是：{concerns[0] if concerns else '信息不够完整，难以下决策'}。",
            ],
            "copy_insights": [
                f"文案或卖点表达里，最该讲清楚的是：{copy_hint[:30]}。",
            ],
            "recommendations": [
                "先把最核心的一条利益点讲透，再补充证明材料和适用场景。",
            ],
        }
        return {key: summary[key] for key in SUMMARY_KEYS}

    def _top_items(self, consumer_voice: List[Dict[str, Any]], key: str) -> List[str]:
        counter = Counter()
        for item in consumer_voice:
            counter.update(item.get(key, []))
        return [value for value, _ in counter.most_common(3)]
