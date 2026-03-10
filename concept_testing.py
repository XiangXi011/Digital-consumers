import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from langgraph_flows import build_analysis_graph as _build_analysis_graph_impl


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class ConceptTestInput:
    concept_name: str
    brand: str
    category: str
    price: float
    core_claims: List[str] = field(default_factory=list)
    packaging_summary: str = ""
    tagline: str = ""
    target_channels: List[str] = field(default_factory=list)
    competitive_anchors: List[str] = field(default_factory=list)
    context_notes: str = ""

    def to_product(self):
        engine = load_legacy_engine()
        selling_points = list(self.core_claims)
        if self.tagline:
            selling_points.append(self.tagline)

        return engine.Product(
            name=self.concept_name,
            brand=self.brand,
            category=self.category,
            price=self.price,
            features=list(self.core_claims),
            selling_points=selling_points,
            packaging={
                "summary": self.packaging_summary,
                "attractive": bool(self.packaging_summary),
            },
            rating=0.0,
            sales_volume=0,
        )


def load_legacy_engine():
    base_dir = Path(__file__).resolve().parent
    engine_path = next(base_dir.glob("digital_consumer_agents*.py"))
    return load_module("digital_consumer_agents_legacy", engine_path)


def build_analysis_graph(runner):
    return _build_analysis_graph_impl(runner)


class ConceptTestRunner:
    def __init__(self, persona_path: Path | str, ai_client: Any | None = None):
        self.base_dir = Path(__file__).resolve().parent
        self.persona_path = Path(persona_path)
        self.ai_client = ai_client
        self.engine = load_legacy_engine()
        self.orchestrator = self.engine.AgentOrchestrator()
        agents = self.engine.load_agents_from_json(str(self.persona_path))
        self.orchestrator.load_agents([agent.to_dict() for agent in agents])
        self.analysis_graph = build_analysis_graph(self)

    def run_batch_evaluation(self, product):
        return self.orchestrator.batch_evaluate(product)

    def select_discussion_participants(self, evaluation_results: List[Dict[str, Any]]) -> List[str]:
        results_by_agent = {result["agent_id"]: result for result in evaluation_results}
        participant_ids: List[str] = []

        for segment_id, agent_ids in sorted(self.orchestrator.segments.items()):
            segment_results = [results_by_agent[agent_id] for agent_id in agent_ids if agent_id in results_by_agent]
            if not segment_results:
                continue

            avg_intention = sum(item["purchase_intention"] for item in segment_results) / len(segment_results)
            representative = min(
                segment_results,
                key=lambda item: (
                    abs(item["purchase_intention"] - avg_intention),
                    -item["overall_score"],
                    item["agent_id"],
                ),
            )
            participant_ids.append(representative["agent_id"])

        return participant_ids[:8]

    def select_deep_dive_candidates(self, evaluation_results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        sorted_results = sorted(
            evaluation_results,
            key=lambda item: (item["purchase_intention"], item["overall_score"], item["agent_id"]),
        )

        used = set()
        rejecting = []
        for item in sorted_results:
            if item["agent_id"] in used:
                continue
            rejecting.append(item["agent_id"])
            used.add(item["agent_id"])
            if len(rejecting) == 2:
                break

        high_intent = []
        for item in reversed(sorted_results):
            if item["agent_id"] in used:
                continue
            high_intent.append(item["agent_id"])
            used.add(item["agent_id"])
            if len(high_intent) == 2:
                break

        hesitant = []
        middle_sorted = sorted(
            evaluation_results,
            key=lambda item: (abs(item["purchase_intention"] - 0.5), -item["overall_score"], item["agent_id"]),
        )
        for item in middle_sorted:
            if item["agent_id"] in used:
                continue
            hesitant.append(item["agent_id"])
            used.add(item["agent_id"])
            if len(hesitant) == 2:
                break

        return {
            "high_intent": high_intent,
            "hesitant": hesitant,
            "rejecting": rejecting,
        }

    def run(self, concept_input: ConceptTestInput) -> Dict[str, Any]:
        state = self.analysis_graph.invoke({"concept_input": concept_input})
        return state["report"]

    def render_markdown_report(self, report: Dict[str, Any]) -> str:
        summary = report["executive_summary"]
        purchase_intent = report["purchase_intent"]
        top_segments = report["segment_opportunity"]["top_segments"]
        weak_segments = report["segment_opportunity"]["weak_segments"]
        consumer_voice = report["voice_of_consumer"]
        barriers = report["barriers"]
        diagnosis = report.get("diagnosis", {})
        action_plan = report.get("action_plan", {})
        report_boundary = report.get("report_boundary", {})

        lines = [
            "# Single Concept Test Report",
            "",
            f"- Concept: {report['meta']['concept_name']}",
            f"- Generated At: {report['meta']['generated_at']}",
            f"- Total Personas: {report['meta']['total_personas']}",
            "",
            "## Executive Summary",
            "",
            f"- Business Recommendation: {summary.get('business_recommendation', summary['recommendation'])}",
            f"- Headline: {summary['headline']}",
            f"- Average Intention: {summary['avg_intention']:.2f}",
            f"- Confidence: {summary.get('confidence_level', '中')} / {summary.get('confidence_reason', '基于当前输入信息生成。')}",
            "",
            "## Decision Drivers",
            "",
        ]

        for item in diagnosis.get("decision_drivers", []):
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Purchase Intent",
                "",
                f"- Estimated Conversion Rate: {purchase_intent['estimated_conversion_rate']}%",
                f"- Decision Distribution: {json.dumps(purchase_intent['decision_distribution'], ensure_ascii=False)}",
                "",
                "## Segment Opportunity",
                "",
                "- Top Segments:",
            ]
        )

        for item in top_segments:
            lines.append(
                f"  - {item['segment']}: intention {item['avg_intention']:.2f}, reason {item.get('why_high_or_low', '待补充')}"
            )

        lines.append("")
        lines.append("- Weak Segments:")
        for item in weak_segments:
            lines.append(
                f"  - {item['segment']}: intention {item['avg_intention']:.2f}, reason {item.get('why_high_or_low', '待补充')}"
            )

        lines.extend(
            [
                "",
                "## Reasons To Buy",
                "",
            ]
        )
        for item in report["reasons_to_buy"]:
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Barriers",
                "",
            ]
        )
        for item in barriers["top_barriers"]:
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Consumer Voice",
                "",
            ]
        )

        for bucket in ["supporters", "hesitant", "rejecting"]:
            lines.append(f"### {bucket.title()}")
            for item in consumer_voice[bucket]:
                lines.append(
                    f"- {item['agent_name']} ({item['segment']}) [{item.get('stance_label', bucket)} / {item.get('reason_tag', '未标注')}]: {item['quote']}"
                )
            lines.append("")

        lines.extend(
            [
                "## Value Proposition Conflicts",
                "",
            ]
        )
        for item in diagnosis.get("value_proposition_conflicts", []):
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Action Plan",
                "",
                "### Immediate Actions",
            ]
        )
        for item in action_plan.get("immediate_actions", []):
            lines.append(f"- {item}")

        lines.extend(["", "### Next-Round Prerequisites"])
        for item in action_plan.get("next_round_prerequisites", []):
            lines.append(f"- {item}")

        lines.extend(["", "### Recommended Next Tests"])
        for item in action_plan.get("recommended_next_tests", []):
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Report Boundary",
                "",
                f"- Input Completeness: {report_boundary.get('input_completeness', 0):.0%}",
            ]
        )
        for item in report_boundary.get("credibility_notes", []):
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## Appendix",
                "",
                f"- Discussion consensus: {report['appendix']['discussion']['consensus_level']:.2f}",
                f"- Deep dive interview count: {report['appendix']['deep_dive_interview_count']}",
            ]
        )

        return "\n".join(lines).strip() + "\n"

    def refresh_report_business_fields(self, report: Dict[str, Any]) -> Dict[str, Any]:
        summary = report["executive_summary"]
        input_summary = report["input_summary"]
        report_boundary = self._build_report_boundary(input_summary, report.get("appendix", {}))
        summary["business_recommendation"] = self._translate_recommendation(summary["recommendation"])
        summary["confidence_level"] = report_boundary["confidence_level"]
        summary["confidence_reason"] = report_boundary["confidence_reason"]
        report["report_boundary"] = {
            "input_completeness": report_boundary["input_completeness"],
            "missing_fields": report_boundary["missing_fields"],
            "credibility_notes": report_boundary["credibility_notes"],
        }
        report["diagnosis"]["competitive_limitations"] = self._build_competitive_limitations(
            input_summary.get("competitive_anchors", [])
        )
        report["optimization_suggestions"] = (
            report.get("action_plan", {}).get("immediate_actions", [])[:2]
            + report.get("action_plan", {}).get("recommended_next_tests", [])[:1]
        )[:4]
        return report

    def save_outputs(self, report: Dict[str, Any], output_dir: Path | str) -> Dict[str, Path]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        slug = self._slugify(report["meta"]["concept_name"])
        json_path = output_path / f"{slug}_report.json"
        md_path = output_path / f"{slug}_report.md"

        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)

        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write(self.render_markdown_report(report))

        return {"json": json_path, "markdown": md_path}

    def _build_report(
        self,
        concept_input: ConceptTestInput,
        product,
        evaluation_results: List[Dict[str, Any]],
        orchestrator_report: Dict[str, Any],
        discussion: Dict[str, Any],
        deep_dives: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        avg_intention = orchestrator_report["summary"]["avg_intention"]
        decision_distribution = orchestrator_report["decision_distribution"]
        recommendation = self._build_recommendation(avg_intention)
        segment_table = self._build_segment_table(orchestrator_report["segment_analysis"], evaluation_results)
        top_segments = segment_table[:3]
        weak_segments = list(reversed(segment_table[-3:])) if segment_table else []
        top_barriers = self._aggregate_barriers(evaluation_results)
        reasons_to_buy = self._aggregate_reasons_to_buy(evaluation_results, concept_input)
        conflicts = self._detect_value_proposition_conflicts(concept_input, avg_intention)
        decision_drivers = self._build_decision_drivers(
            concept_input=concept_input,
            top_barriers=top_barriers,
            top_segments=top_segments,
            weak_segments=weak_segments,
            conflicts=conflicts,
        )
        action_plan = self._build_action_plan(
            barriers=top_barriers,
            top_segments=top_segments,
            weak_segments=weak_segments,
            concept_input=concept_input,
            conflicts=conflicts,
        )

        report = {
            "meta": {
                "concept_name": concept_input.concept_name,
                "brand": concept_input.brand,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_personas": len(evaluation_results),
            },
            "input_summary": {
                "category": concept_input.category,
                "price": concept_input.price,
                "core_claims": concept_input.core_claims,
                "packaging_summary": concept_input.packaging_summary,
                "tagline": concept_input.tagline,
                "target_channels": concept_input.target_channels,
                "competitive_anchors": concept_input.competitive_anchors,
                "context_notes": concept_input.context_notes,
                "missing_fields": [],
                "packaging_image_path": "",
            },
            "executive_summary": {
                "headline": self._build_headline(avg_intention, top_segments),
                "recommendation": recommendation,
                "business_recommendation": self._translate_recommendation(recommendation),
                "avg_intention": avg_intention,
                "key_risk": top_barriers[0] if top_barriers else "还需要更多真实消费者证据支撑。",
            },
            "purchase_intent": {
                "average_score": orchestrator_report["summary"]["avg_score"],
                "average_intention": avg_intention,
                "estimated_conversion_rate": orchestrator_report["summary"]["estimated_conversion_rate"],
                "decision_distribution": decision_distribution,
            },
            "segment_opportunity": {
                "top_segments": top_segments,
                "weak_segments": weak_segments,
                "full_table": segment_table,
            },
            "reasons_to_buy": reasons_to_buy,
            "barriers": {
                "top_barriers": top_barriers,
                "price_concern_share": self._calculate_price_concern_share(evaluation_results),
            },
            "diagnosis": {
                "decision_drivers": decision_drivers,
                "value_proposition_conflicts": conflicts,
                "competitive_limitations": self._build_competitive_limitations(concept_input.competitive_anchors),
            },
            "voice_of_consumer": self._build_voice_of_consumer(evaluation_results, discussion, deep_dives),
            "action_plan": action_plan,
            "optimization_suggestions": (
                action_plan["immediate_actions"][:2] + action_plan["recommended_next_tests"][:1]
            )[:4],
            "appendix": {
                "discussion": discussion,
                "deep_dives": deep_dives,
                "deep_dive_interview_count": sum(len(items) for items in deep_dives.values()),
            },
        }
        return self.refresh_report_business_fields(report)

    def _build_segment_table(
        self,
        segment_analysis: Dict[str, Dict[str, Any]],
        evaluation_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results_by_segment = defaultdict(list)
        for item in evaluation_results:
            results_by_segment[item["segment"]].append(item)

        table = []
        for segment, stats in segment_analysis.items():
            segment_results = results_by_segment.get(segment, [])
            top_reason_tag = self._derive_segment_reason_tag(segment_results)
            table.append(
                {
                    "segment": segment,
                    "count": stats["count"],
                    "avg_score": stats["avg_score"],
                    "avg_intention": stats["avg_intention"],
                    "why_high_or_low": self._summarize_segment_reason(
                        segment=segment,
                        segment_results=segment_results,
                        avg_intention=stats["avg_intention"],
                        top_reason_tag=top_reason_tag,
                    ),
                    "top_reason_tag": top_reason_tag,
                }
            )
        return sorted(table, key=lambda item: (-item["avg_intention"], -item["avg_score"], item["segment"]))

    def _aggregate_barriers(self, evaluation_results: List[Dict[str, Any]]) -> List[str]:
        counter = Counter()
        for item in evaluation_results:
            for concern in item.get("key_concerns", []):
                counter[concern] += 1

        if counter:
            return [entry[0] for entry in counter.most_common(3)]

        avg_price_factor = sum(item.get("price_evaluation", 0) for item in evaluation_results) / len(evaluation_results)
        if avg_price_factor < 0.5:
            return ["当前价格感知偏高，价值感支撑不足。"]

        return [
            "产品利益点证明还不够清晰。",
            "当前价值主张的差异化还不够强。",
        ]

    def _aggregate_reasons_to_buy(
        self,
        evaluation_results: List[Dict[str, Any]],
        concept_input: ConceptTestInput,
    ) -> List[str]:
        counter = Counter()
        positive_results = [
            item for item in evaluation_results if item.get("purchase_intention", 0) >= 0.5
        ]
        for item in positive_results:
            for feature in item.get("preferred_features", []):
                counter[feature] += 1

        if counter:
            return [entry[0] for entry in counter.most_common(3)]

        fallback = list(concept_input.core_claims[:3])
        if concept_input.tagline:
            fallback.append(concept_input.tagline)
        return fallback[:3]

    def _calculate_price_concern_share(self, evaluation_results: List[Dict[str, Any]]) -> float:
        if not evaluation_results:
            return 0.0
        price_concerns = 0
        for item in evaluation_results:
            if any("价" in concern or "Price" in concern for concern in item.get("key_concerns", [])):
                price_concerns += 1
        return round(price_concerns / len(evaluation_results), 2)

    def _build_voice_of_consumer(
        self,
        evaluation_results: List[Dict[str, Any]],
        discussion: Dict[str, Any],
        deep_dives: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, str]]]:
        grouped = {
            "supporters": [],
            "hesitant": [],
            "rejecting": [],
        }

        discussion_by_agent = {item["agent_id"]: item for item in discussion.get("opinions", [])}
        deep_dive_by_agent = {}
        for bucket in deep_dives.values():
            for item in bucket:
                deep_dive_by_agent[item["agent_id"]] = item

        supporters = sorted(
            [item for item in evaluation_results if item.get("purchase_intention", 0) >= 0.5],
            key=lambda item: (-item.get("purchase_intention", 0), -item.get("overall_score", 0), item["agent_id"]),
        )
        hesitant = sorted(
            [
                item
                for item in evaluation_results
                if item.get("decision") == "犹豫观望" or 0.3 <= item.get("purchase_intention", 0) < 0.5
            ],
            key=lambda item: (abs(item.get("purchase_intention", 0) - 0.45), -item.get("overall_score", 0), item["agent_id"]),
        )
        rejecting = sorted(
            [
                item
                for item in evaluation_results
                if item.get("decision") == "明确拒绝" or item.get("purchase_intention", 0) < 0.3
            ],
            key=lambda item: (item.get("purchase_intention", 0), item.get("overall_score", 0), item["agent_id"]),
        )

        grouped["supporters"] = [
            self._build_voice_entry(item, "支持者", discussion_by_agent.get(item["agent_id"]), deep_dive_by_agent.get(item["agent_id"]))
            for item in supporters[:3]
        ]
        grouped["hesitant"] = [
            self._build_voice_entry(item, "犹豫者", discussion_by_agent.get(item["agent_id"]), deep_dive_by_agent.get(item["agent_id"]))
            for item in hesitant[:3]
        ]
        grouped["rejecting"] = [
            self._build_voice_entry(item, "拒绝者", discussion_by_agent.get(item["agent_id"]), deep_dive_by_agent.get(item["agent_id"]))
            for item in rejecting[:3]
        ]

        return grouped

    def _build_action_plan(
        self,
        barriers: List[str],
        top_segments: List[Dict[str, Any]],
        weak_segments: List[Dict[str, Any]],
        concept_input: ConceptTestInput,
        conflicts: List[str],
    ) -> Dict[str, List[str]]:
        immediate_actions = []
        next_round_prerequisites = []
        recommended_next_tests = []

        if len(concept_input.core_claims) >= 5:
            immediate_actions.append("收敛主卖点到 1 个核心利益点 + 2 个辅助支撑点，避免首轮外测信息过载。")
        if any("安全" in barrier or "成分" in barrier or "含氟" in barrier for barrier in barriers):
            immediate_actions.append("把“安全含氟 + 安全测试”前置到首屏，优先建立家长的安全信任感。")
        if any("美白" in conflict or "净色" in conflict for conflict in conflicts):
            immediate_actions.append("弱化儿童场景下的“健白/净色”表达，优先突出安全防蛀与趣味刷牙闭环。")
        if concept_input.packaging_summary:
            immediate_actions.append("优化包装首屏信息层级，让主利益点在第一眼就能被理解。")

        if not concept_input.competitive_anchors:
            next_round_prerequisites.append("补充 2-4 个核心竞品锚点，避免下一轮仍停留在单概念自洽性判断。")
        if not concept_input.packaging_summary:
            next_round_prerequisites.append("补充包装首屏 mockup 或详情页主视觉，提升包装判断可信度。")
        if not concept_input.target_channels:
            next_round_prerequisites.append("补充目标渠道信息，便于判断价格带与表达风格是否匹配。")
        next_round_prerequisites.append("准备主副文案版本 A/B，用于验证价值主张收敛后的接受度变化。")

        if conflicts:
            recommended_next_tests.append("版本 A 主打温和安全防蛀，版本 B 主打趣味刷牙监督，对比哪条主轴更成立。")
        else:
            recommended_next_tests.append("围绕当前主卖点做 A/B 文案测试，验证首屏价值表达是否足够清晰。")
        if top_segments:
            recommended_next_tests.append(
                f"优先在 {top_segments[0]['segment']} 中做下一轮验证，提升早期命中率。"
            )
        if weak_segments:
            recommended_next_tests.append(
                f"谨慎在 {weak_segments[0]['segment']} 投放首轮外测，除非同步调整产品定位。"
            )

        return {
            "immediate_actions": immediate_actions[:3] or ["先明确一个最强购买理由，再进入外部测试。"],
            "next_round_prerequisites": next_round_prerequisites[:3],
            "recommended_next_tests": recommended_next_tests[:3],
        }

    def _build_report_boundary(self, input_summary: Dict[str, Any], appendix: Dict[str, Any]) -> Dict[str, Any]:
        missing_fields = list(input_summary.get("missing_fields", []))
        total_fields = 14
        input_completeness = max(0.0, round((total_fields - len(missing_fields)) / total_fields, 2))

        evidence_score = input_completeness * 100
        if input_summary.get("price"):
            evidence_score += 5
        if input_summary.get("packaging_summary") or input_summary.get("packaging_image_path"):
            evidence_score += 5
        if input_summary.get("target_channels"):
            evidence_score += 5
        if input_summary.get("competitive_anchors"):
            evidence_score += 5
        if appendix.get("discussion"):
            evidence_score += 5
        if appendix.get("deep_dive_interview_count", 0):
            evidence_score += 5
        evidence_score = min(100, evidence_score)

        if evidence_score >= 90:
            confidence_level = "高"
        elif evidence_score >= 75:
            confidence_level = "中高"
        elif evidence_score >= 60:
            confidence_level = "中"
        else:
            confidence_level = "低"

        strengths = []
        if input_summary.get("core_claims"):
            strengths.append("核心概念")
        if input_summary.get("price"):
            strengths.append("价格")
        if input_summary.get("target_channels"):
            strengths.append("渠道")
        if input_summary.get("packaging_summary") or input_summary.get("packaging_image_path"):
            strengths.append("包装素材")

        gaps = []
        if not input_summary.get("competitive_anchors"):
            gaps.append("竞品锚点")
        if missing_fields:
            gaps.append(f"仍缺少 {len(missing_fields)} 项输入信息")

        strength_text = "、".join(strengths) if strengths else "基础输入信息"
        gap_text = "；".join(gaps) if gaps else "核心输入与分析证据较完整"
        confidence_reason = f"{strength_text}已提供，当前结论可信度为{confidence_level}；{gap_text}。"

        credibility_notes = [confidence_reason]
        if not input_summary.get("competitive_anchors"):
            credibility_notes.append("由于未提供竞品参考，本次更偏单概念自洽性判断，不包含相对竞争优势评估。")
        if missing_fields:
            credibility_notes.append(f"以下缺失项会影响结论稳健性：{'、'.join(missing_fields)}。")

        return {
            "input_completeness": input_completeness,
            "confidence_level": confidence_level,
            "confidence_reason": confidence_reason,
            "missing_fields": missing_fields,
            "credibility_notes": credibility_notes,
        }

    def _build_competitive_limitations(self, competitive_anchors: List[str]) -> List[str]:
        if competitive_anchors:
            return ["本次已提供竞品锚点，但当前结论仍以单概念验证为主，相对优势判断仍需下一轮对比测试。"]
        return ["由于未提供竞品参考，本次结论更偏单概念自洽性判断，不包含相对竞争优势评估。"]

    def _build_decision_drivers(
        self,
        concept_input: ConceptTestInput,
        top_barriers: List[str],
        top_segments: List[Dict[str, Any]],
        weak_segments: List[Dict[str, Any]],
        conflicts: List[str],
    ) -> List[str]:
        drivers: List[str] = []

        if len(concept_input.core_claims) >= 5:
            drivers.append("卖点数量过多，核心记忆点分散，消费者难以快速理解主价值。")
        if top_barriers:
            barrier = top_barriers[0]
            if any(token in barrier for token in ["安全", "成分", "含氟"]):
                drivers.append("安全性虽有表述，但尚未形成足够强的信任闭环。")
            else:
                drivers.append(f"当前主要阻力集中在“{barrier}”，说明概念说服力仍有明显短板。")
        if conflicts:
            drivers.append(conflicts[0])
        if top_segments and weak_segments:
            gap = top_segments[0]["avg_intention"] - weak_segments[0]["avg_intention"]
            if gap >= 0.25:
                drivers.append("不同人群接受度差异较大，说明当前价值主张的人群适配性还不够均衡。")
        if not drivers:
            drivers.append("当前概念仍缺少一个足够突出的购买理由，消费者难以快速建立偏好。")

        return drivers[:3]

    def _detect_value_proposition_conflicts(
        self,
        concept_input: ConceptTestInput,
        avg_intention: float,
    ) -> List[str]:
        all_text = " ".join(concept_input.core_claims + [concept_input.tagline, concept_input.context_notes])
        themes = self._collect_claim_themes(all_text, concept_input.core_claims)
        conflicts = []

        if len(themes) >= 4 or len(concept_input.core_claims) >= 5:
            conflicts.append("当前卖点数量过多，主次不清，消费者容易抓不住最核心的价值主张。")
        if "美白净色" in themes and "安全温和" in themes and "儿童" in concept_input.category:
            conflicts.append("儿童场景下，“健白/净色”与“安全温和”之间存在潜在认知张力。")
        if "趣味互动" in themes and "防蛀功效" in themes and avg_intention < 0.45:
            conflicts.append("“趣味互动”具传播性，但与核心功效闭环连接还不够自然。")
        if not conflicts and len(themes) >= 3:
            conflicts.append("当前价值表达层次较多，建议进一步明确一个最强主轴。")

        return conflicts[:3]

    def _collect_claim_themes(self, all_text: str, claims: List[str]) -> List[str]:
        themes = set()
        text = all_text or " ".join(claims)

        if any(token in text for token in ["防蛀", "抗糖", "蛀", "防护层"]):
            themes.add("防蛀功效")
        if any(token in text for token in ["安全", "温和", "低氟", "含氟", "无刺激", "软性磨料"]):
            themes.add("安全温和")
        if any(token in text for token in ["变色", "趣味", "可视化", "孩子更愿意", "刷牙过程"]):
            themes.add("趣味互动")
        if any(token in text for token in ["健白", "净白", "净齿", "色斑", "小白牙"]):
            themes.add("美白净色")
        if any(token in text for token in ["科学", "测试", "CPP", "HAP", "临床", "证据"]):
            themes.add("科学背书")

        return sorted(themes)

    def _derive_segment_reason_tag(self, segment_results: List[Dict[str, Any]]) -> str:
        if not segment_results:
            return "样本不足"

        concern_counter = Counter()
        feature_counter = Counter()
        for item in segment_results:
            concern_counter.update(self._normalize_reason_tag(value) for value in item.get("key_concerns", []))
            feature_counter.update(self._normalize_reason_tag(value) for value in item.get("preferred_features", []))

        if feature_counter:
            return feature_counter.most_common(1)[0][0]
        if concern_counter:
            return concern_counter.most_common(1)[0][0]
        return self._normalize_reason_tag(segment_results[0].get("reasoning", "价值感判断"))

    def _summarize_segment_reason(
        self,
        segment: str,
        segment_results: List[Dict[str, Any]],
        avg_intention: float,
        top_reason_tag: str,
    ) -> str:
        concern_counter = Counter()
        for item in segment_results:
            concern_counter.update(self._normalize_reason_tag(value) for value in item.get("key_concerns", []))
        top_concern = concern_counter.most_common(1)[0][0] if concern_counter else ""

        if avg_intention >= 0.5:
            if top_concern:
                return f"对“{top_reason_tag}”有明显感知，但仍会继续确认“{top_concern}”是否足够可信。"
            return f"对“{top_reason_tag}”反应较好，当前与该人群的需求匹配度相对更高。"
        if avg_intention >= 0.3:
            if top_concern:
                return f"能理解“{top_reason_tag}”的吸引力，但在“{top_concern}”上仍然犹豫。"
            return f"对价值点有一定兴趣，但当前购买理由还不足以形成稳定转化。"
        if top_concern:
            return f"更容易被“{top_concern}”阻断，对“{top_reason_tag}”的感知不足，因此接受度偏低。"
        return "当前价值表达尚未击中这个人群的核心决策逻辑，因此接受度偏低。"

    def _build_voice_entry(
        self,
        evaluation: Dict[str, Any],
        stance_label: str,
        discussion_entry: Dict[str, Any] | None,
        deep_dive_entry: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        reason_tag = self._derive_reason_tag(evaluation, deep_dive_entry)
        fallback_quote = self._synthesize_voice_quote(stance_label, reason_tag)
        quote = fallback_quote
        quote_generation_mode = "fallback_rule"
        quote_validation = {
            "mode": "not_attempted",
            "is_consistent": False,
            "detected_stance": "",
            "detected_reason": "",
            "why": "LLM quote generation was not attempted.",
        }

        llm_result = self._try_generate_llm_quote(
            evaluation=evaluation,
            stance_label=stance_label,
            reason_tag=reason_tag,
            discussion_entry=discussion_entry,
            deep_dive_entry=deep_dive_entry,
        )
        if llm_result.get("quote"):
            validation_result = self._try_validate_generated_quote(
                expected_stance=stance_label,
                expected_reason_tag=reason_tag,
                quote=llm_result["quote"],
            )
            if validation_result["is_consistent"]:
                quote = llm_result["quote"]
                quote_generation_mode = llm_result.get("mode", "llm_quote")
            else:
                quote_generation_mode = "fallback_rule_after_validation"
            quote_validation = validation_result
        elif llm_result.get("error"):
            quote_generation_mode = "fallback_rule_error"
            quote_validation = {
                "mode": "skipped_after_generation_error",
                "is_consistent": False,
                "detected_stance": "",
                "detected_reason": "",
                "why": str(llm_result["error"]),
            }

        return {
            "agent_name": evaluation.get("agent_name") or (discussion_entry or {}).get("agent_name", "匿名用户"),
            "segment": evaluation.get("segment") or (discussion_entry or {}).get("segment", "未知人群"),
            "stance_label": stance_label,
            "reason_tag": reason_tag,
            "quote": quote,
            "quote_generation_mode": quote_generation_mode,
            "quote_validation": quote_validation,
        }

    def _try_generate_llm_quote(
        self,
        evaluation: Dict[str, Any],
        stance_label: str,
        reason_tag: str,
        discussion_entry: Dict[str, Any] | None,
        deep_dive_entry: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        if not self.ai_client or not hasattr(self.ai_client, "generate_consumer_quote"):
            return {"mode": "fallback_quote", "quote": ""}

        payload = {
            "agent_name": evaluation.get("agent_name") or (discussion_entry or {}).get("agent_name", ""),
            "segment": evaluation.get("segment") or (discussion_entry or {}).get("segment", ""),
            "stance_label": stance_label,
            "reason_tag": reason_tag,
            "purchase_intention": evaluation.get("purchase_intention", ""),
            "decision": evaluation.get("decision", ""),
            "reasoning": evaluation.get("reasoning", ""),
            "key_concerns": evaluation.get("key_concerns", []),
            "preferred_features": evaluation.get("preferred_features", []),
            "discussion_signal": (discussion_entry or {}).get("response", ""),
            "deep_dive_signal": self._extract_deep_dive_signal(deep_dive_entry),
        }
        try:
            result = self.ai_client.generate_consumer_quote(payload)
        except Exception as exc:
            return {"mode": "fallback_quote", "quote": "", "error": exc}

        quote = str(result.get("quote", "")).strip()
        if not quote:
            return {"mode": result.get("mode", "fallback_quote"), "quote": ""}
        return {"mode": result.get("mode", "llm_quote"), "quote": quote}

    def _extract_deep_dive_signal(self, deep_dive_entry: Dict[str, Any] | None) -> str:
        if not deep_dive_entry:
            return ""
        responses = deep_dive_entry.get("interview_responses", [])
        if not responses:
            return ""
        parts = []
        for item in responses[:2]:
            answer = item.get("answer", "")
            motivation = item.get("underlying_motivation", "")
            if answer:
                parts.append(str(answer))
            if motivation:
                parts.append(str(motivation))
        return " ".join(part for part in parts if part)

    def _try_validate_generated_quote(
        self,
        expected_stance: str,
        expected_reason_tag: str,
        quote: str,
    ) -> Dict[str, Any]:
        if not self.ai_client or not hasattr(self.ai_client, "validate_consumer_quote"):
            return {
                "mode": "validation_unavailable",
                "is_consistent": False,
                "detected_stance": "",
                "detected_reason": "",
                "why": "AI quote validation is unavailable.",
            }
        try:
            result = self.ai_client.validate_consumer_quote(expected_stance, expected_reason_tag, quote)
        except Exception as exc:
            return {
                "mode": "validation_error",
                "is_consistent": False,
                "detected_stance": "",
                "detected_reason": "",
                "why": str(exc),
            }

        detected_stance = str(result.get("detected_stance", "")).strip()
        detected_reason = str(result.get("detected_reason", "")).strip()
        is_consistent = bool(result.get("is_consistent")) and detected_stance == expected_stance
        if is_consistent and detected_reason:
            is_consistent = self._reason_tags_match(expected_reason_tag, detected_reason)

        return {
            "mode": result.get("mode", "live_validation"),
            "is_consistent": is_consistent,
            "detected_stance": detected_stance,
            "detected_reason": detected_reason,
            "why": str(result.get("why", "")).strip(),
        }

    def _reason_tags_match(self, expected_reason_tag: str, detected_reason: str) -> bool:
        if not detected_reason:
            return False
        return self._normalize_reason_tag(expected_reason_tag) == self._normalize_reason_tag(detected_reason)

    def _derive_reason_tag(self, evaluation: Dict[str, Any], deep_dive_entry: Dict[str, Any] | None) -> str:
        if evaluation.get("key_concerns"):
            return self._normalize_reason_tag(evaluation["key_concerns"][0])
        if evaluation.get("preferred_features"):
            return self._normalize_reason_tag(evaluation["preferred_features"][0])
        if deep_dive_entry and deep_dive_entry.get("interview_responses"):
            response = deep_dive_entry["interview_responses"][0]
            motivation = response.get("underlying_motivation") or response.get("emotional_trigger")
            if motivation:
                return self._normalize_reason_tag(motivation)
        return self._normalize_reason_tag(evaluation.get("reasoning", "价值判断"))

    def _synthesize_voice_quote(self, stance_label: str, reason_tag: str) -> str:
        phrase = self._render_reason_phrase(reason_tag, stance_label)
        if stance_label == "支持者":
            return f"我能感受到这个方案在“{phrase}”上的优势，整体看下来我愿意尝试。"
        if stance_label == "犹豫者":
            return f"我能理解“{phrase}”这个点，但现在还缺一点让我放心下单的理由。"
        return f"我更看重稳妥和确定性，现在最担心“{phrase}”，所以暂时不会买。"

    def _render_reason_phrase(self, reason_tag: str, stance_label: str) -> str:
        positive = {
            "价格敏感": "价格还算合适",
            "专业背书": "专业可信度",
            "包装吸引力": "包装第一眼吸引力",
            "趣味刷牙": "趣味刷牙体验",
            "防蛀功效": "防蛀功效表达",
            "美白净色": "净白感知",
            "稳妥偏好": "稳妥安心感",
            "信息过载": "信息收敛度",
            "安全感不足": "安全说明",
            "价值判断": "整体价值表达",
        }
        negative = {
            "价格敏感": "价格值不值",
            "专业背书": "专业背书是否够硬",
            "包装吸引力": "包装好看但未必能支撑购买",
            "趣味刷牙": "趣味点能不能真正带来持续使用",
            "防蛀功效": "防蛀说服力是否足够",
            "美白净色": "儿童场景下的净白表达是否合适",
            "稳妥偏好": "是不是足够稳妥",
            "信息过载": "卖点太多看不清重点",
            "安全感不足": "安全感是否足够",
            "价值判断": "整体价值感是否成立",
        }
        if stance_label == "支持者":
            return positive.get(reason_tag, reason_tag)
        return negative.get(reason_tag, reason_tag)

    def _normalize_reason_tag(self, raw_text: str) -> str:
        text = str(raw_text or "").strip()
        mapping = [
            (["安全", "成分", "含氟", "无刺激"], "安全感不足"),
            (["价格", "预算", "贵", "性价比"], "价格敏感"),
            (["品牌", "专业", "权威", "背书", "测试", "临床"], "专业背书"),
            (["包装", "颜值", "好看", "高级"], "包装吸引力"),
            (["变色", "趣味", "可视化", "孩子"], "趣味刷牙"),
            (["防蛀", "抗糖", "功效", "防护"], "防蛀功效"),
            (["健白", "净白", "色斑", "小白牙"], "美白净色"),
            (["稳妥", "老牌", "放心"], "稳妥偏好"),
            (["太多", "复杂", "分散"], "信息过载"),
        ]
        for keywords, label in mapping:
            if any(keyword in text for keyword in keywords):
                return label

        cleaned = re.sub(r"^[担心觉得认为想要会先更看重]+", "", text)
        cleaned = cleaned.strip("。；，, ")
        return cleaned or "价值判断"

    def _build_headline(self, avg_intention: float, top_segments: List[Dict[str, Any]]) -> str:
        if avg_intention >= 0.65:
            return "该概念在数字消费者样本中表现出较强的早期吸引力。"
        if avg_intention >= 0.45:
            if top_segments:
                return f"该概念有一定潜力，但不同人群接受度不均衡，当前最匹配的人群是 {top_segments[0]['segment']}。"
            return "该概念有一定潜力，但当前在不同细分人群中的接受度仍不均衡。"
        return "该概念暂不建议直接进入外部测试，当前价值定义仍需进一步聚焦。"

    def _build_recommendation(self, avg_intention: float) -> str:
        if avg_intention >= 0.65:
            return "advance_to_real_research"
        if avg_intention >= 0.45:
            return "revise_then_retest"
        return "do_not_advance_yet"

    def _translate_recommendation(self, recommendation: str) -> str:
        mapping = {
            "advance_to_real_research": "可进入真实外部调研",
            "revise_then_retest": "建议优化后再进行下一轮测试",
            "do_not_advance_yet": "建议先内部优化，不建议直接进入外部测试",
        }
        return mapping.get(recommendation, recommendation)

    def _build_discussion_topic(self, concept_input: ConceptTestInput) -> str:
        if concept_input.tagline:
            return f"Would you buy this concept: {concept_input.tagline}"
        return f"Would you buy this concept: {concept_input.concept_name}"

    def _build_deep_dive_questions(self, concept_input: ConceptTestInput) -> List[str]:
        return [
            f"What is your first reaction to {concept_input.concept_name}?",
            "Which element makes you most likely or least likely to buy?",
            "What would need to change before you would feel confident buying it?",
        ]

    def _slugify(self, value: str) -> str:
        cleaned = []
        for char in value.lower():
            if char.isalnum():
                cleaned.append(char)
            elif char in {" ", "-", "_"}:
                cleaned.append("_")
        slug = "".join(cleaned).strip("_")
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug or "single_concept"
