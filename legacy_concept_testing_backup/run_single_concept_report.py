from pathlib import Path

from concept_testing import ConceptTestInput, ConceptTestRunner


def build_sample_concept() -> ConceptTestInput:
    return ConceptTestInput(
        concept_name="舒客儿童益生菌防蛀牙膏概念版",
        brand="舒客",
        category="儿童口腔护理",
        price=39.9,
        core_claims=[
            "益生菌配方",
            "低氟防蛀",
            "孩子更愿意坚持刷牙",
        ],
        packaging_summary="卡通水果视觉，正面突出年龄段和防蛀卖点。",
        tagline="一支让孩子愿意每天使用的防蛀牙膏。",
        target_channels=["天猫", "京东", "母婴店"],
        competitive_anchors=["欧乐B儿童牙膏", "Putzi"],
        context_notes="用于正式消费者调研前的概念预验证。",
    )


def main():
    base_dir = Path(__file__).resolve().parent
    runner = ConceptTestRunner(base_dir / "persona_samples_complete.json")
    report = runner.run(build_sample_concept())
    output_paths = runner.save_outputs(report, base_dir / "outputs")

    print("Single concept report generated.")
    print(f"JSON: {output_paths['json']}")
    print(f"Markdown: {output_paths['markdown']}")


if __name__ == "__main__":
    main()
