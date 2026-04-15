import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ai_clients import BaseAIClient, OpenAICompatibleClient


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_concept_testing_module():
    base_dir = Path(__file__).resolve().parent
    return load_module("concept_testing_runtime", base_dir / "concept_testing.py")


class AdvancedTestRunner:
    def __init__(self, persona_path: Path | str, ai_client: BaseAIClient | None = None):
        self.base_dir = Path(__file__).resolve().parent
        self.persona_path = Path(persona_path)
        self.ai_client = ai_client or OpenAICompatibleClient()
        self.concept_testing = load_concept_testing_module()
        self.runner = self.concept_testing.ConceptTestRunner(self.persona_path, ai_client=self.ai_client)
        self.orchestrator = self.runner.orchestrator

    def run_single_concept_with_ai(self, concept_input):
        report = self.runner.run(concept_input)
        llm_summary = self.ai_client.generate_text(
            prompt=self._build_summary_prompt(report),
            system_prompt="You are a market research analyst. Summarize the concept test clearly and concisely.",
        )
        report["executive_summary"]["llm_summary"] = llm_summary["text"]
        report["meta"]["text_generation_mode"] = llm_summary["mode"]
        return report

    def run_ab_comparison(self, concept_a, concept_b) -> Dict[str, Any]:
        report_a = self.runner.run(concept_a)
        report_b = self.runner.run(concept_b)

        avg_a = report_a["purchase_intent"]["average_intention"]
        avg_b = report_b["purchase_intent"]["average_intention"]
        if avg_a > avg_b:
            winner = "A"
        elif avg_b > avg_a:
            winner = "B"
        else:
            winner = "tie"

        segment_deltas = []
        segments_a = {row["segment"]: row for row in report_a["segment_opportunity"]["full_table"]}
        segments_b = {row["segment"]: row for row in report_b["segment_opportunity"]["full_table"]}
        for segment in sorted(set(segments_a) | set(segments_b)):
            score_a = segments_a.get(segment, {}).get("avg_intention", 0)
            score_b = segments_b.get(segment, {}).get("avg_intention", 0)
            segment_deltas.append(
                {
                    "segment": segment,
                    "variant_a_intention": score_a,
                    "variant_b_intention": score_b,
                    "delta": round(score_a - score_b, 2),
                    "winner": "A" if score_a > score_b else "B" if score_b > score_a else "tie",
                }
            )

        return {
            "variant_a": report_a,
            "variant_b": report_b,
            "winner": winner,
            "delta_avg_intention": round(avg_a - avg_b, 2),
            "segment_deltas": segment_deltas,
        }

    def run_price_ladder(self, concept_input, prices: List[float]) -> Dict[str, Any]:
        price_points = []
        previous_intention = None
        drop_off_point = None

        for price in prices:
            concept_variant = deepcopy(concept_input)
            concept_variant.price = price
            report = self.runner.run(concept_variant)
            current_intention = report["purchase_intent"]["average_intention"]

            if previous_intention is not None and drop_off_point is None and current_intention < previous_intention - 0.08:
                drop_off_point = price

            price_points.append(
                {
                    "price": price,
                    "average_intention": current_intention,
                    "estimated_conversion_rate": report["purchase_intent"]["estimated_conversion_rate"],
                }
            )
            previous_intention = current_intention

        best_point = max(price_points, key=lambda item: (item["average_intention"], -item["price"]))
        sorted_points = sorted(price_points, key=lambda item: item["price"])

        return {
            "concept_name": concept_input.concept_name,
            "price_points": sorted_points,
            "recommended_price_zone": {
                "target_price": best_point["price"],
                "reason": "Highest modeled intention with current concept configuration.",
            },
            "drop_off_point": drop_off_point,
        }

    def run_packaging_review(self, concept_input, image_path: Path | str) -> Dict[str, Any]:
        image_path = Path(image_path)
        visual_result = self.ai_client.analyze_image(
            image_path=image_path,
            prompt=(
                "Describe this children packaging image for a market concept test. "
                "Focus on clarity, child appeal, safety cues, premium feel, and whether the main benefit is easy to understand."
            ),
        )

        concept_variant = deepcopy(concept_input)
        concept_variant.packaging_summary = visual_result["text"]
        single_report = self.run_single_concept_with_ai(concept_variant)

        return {
            "packaging_review": {
                "image_path": str(image_path),
                "analysis_mode": visual_result["mode"],
                "visual_summary": visual_result["text"],
                "structured_signals": visual_result.get("structured_signals", {}),
            },
            "single_concept_report": single_report,
        }

    def render_ab_markdown(self, report: Dict[str, Any]) -> str:
        return "\n".join(
            [
                "# A/B Concept Comparison Report",
                "",
                f"- Winner: {report['winner']}",
                f"- Delta Intention: {report['delta_avg_intention']:.2f}",
                "",
                "## Segment Deltas",
                "",
            ]
            + [
                f"- {item['segment']}: A {item['variant_a_intention']:.2f} vs B {item['variant_b_intention']:.2f} ({item['winner']})"
                for item in report["segment_deltas"][:8]
            ]
        ) + "\n"

    def render_price_ladder_markdown(self, report: Dict[str, Any]) -> str:
        lines = [
            "# Price Ladder Report",
            "",
            f"- Concept: {report['concept_name']}",
            f"- Recommended Price: {report['recommended_price_zone']['target_price']}",
            f"- Drop-off Point: {report['drop_off_point']}",
            "",
            "## Price Points",
            "",
        ]
        for item in report["price_points"]:
            lines.append(
                f"- {item['price']}: intention {item['average_intention']:.2f}, conversion {item['estimated_conversion_rate']}%"
            )
        return "\n".join(lines) + "\n"

    def render_packaging_markdown(self, report: Dict[str, Any]) -> str:
        return "\n".join(
            [
                "# Packaging Review Report",
                "",
                f"- Image: {report['packaging_review']['image_path']}",
                f"- Analysis Mode: {report['packaging_review']['analysis_mode']}",
                "",
                "## Visual Summary",
                "",
                report["packaging_review"]["visual_summary"],
                "",
                "## Structured Signals",
                "",
            ]
            + [
                f"- {key}: {value}"
                for key, value in report["packaging_review"]["structured_signals"].items()
            ]
        ) + "\n"

    def _build_summary_prompt(self, report: Dict[str, Any]) -> str:
        return (
            f"Concept: {report['meta']['concept_name']}\n"
            f"Average intention: {report['purchase_intent']['average_intention']}\n"
            f"Estimated conversion: {report['purchase_intent']['estimated_conversion_rate']}%\n"
            f"Top barriers: {report['barriers']['top_barriers']}\n"
            f"Top segments: {report['segment_opportunity']['top_segments']}\n"
            "Write a concise executive summary."
        )


def build_sample_single_input():
    concept_testing = load_concept_testing_module()
    return concept_testing.ConceptTestInput(
        concept_name="舒客儿童益生菌防蛀牙膏概念版",
        brand="舒客",
        category="儿童口腔护理",
        price=39.9,
        core_claims=["益生菌配方", "低氟防蛀", "孩子更愿意坚持刷牙"],
        packaging_summary="卡通水果视觉，正面突出年龄段和防蛀卖点。",
        tagline="一支让孩子愿意每天使用的防蛀牙膏。",
        target_channels=["天猫", "京东", "母婴店"],
        competitive_anchors=["欧乐B儿童牙膏", "Putzi"],
        context_notes="用于正式消费者调研前的概念预验证。",
    )


def build_sample_ab_inputs() -> Tuple[Any, Any]:
    concept_a = build_sample_single_input()
    concept_b = deepcopy(concept_a)
    concept_b.concept_name = "舒客儿童防蛀牙膏清爽版"
    concept_b.price = 34.9
    concept_b.core_claims = ["清爽水果口味", "基础防蛀", "高性价比"]
    concept_b.packaging_summary = "更简洁的清爽包装，突出价格和基础防蛀。"
    concept_b.tagline = "更轻决策的儿童防蛀牙膏选择。"
    return concept_a, concept_b
