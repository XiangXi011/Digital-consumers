import json
from pathlib import Path

from advanced_testing import AdvancedTestRunner, build_sample_ab_inputs


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = AdvancedTestRunner(base_dir / "persona_samples_complete.json")
    concept_a, concept_b = build_sample_ab_inputs()
    report = runner.run_ab_comparison(concept_a, concept_b)

    json_path = output_dir / "ab_test_report.json"
    md_path = output_dir / "ab_test_report.md"

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(runner.render_ab_markdown(report))

    print("A/B report generated.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
