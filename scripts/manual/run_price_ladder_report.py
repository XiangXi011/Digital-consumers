import json
from pathlib import Path

from advanced_testing import AdvancedTestRunner, build_sample_single_input


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = AdvancedTestRunner(base_dir / "persona_samples_complete.json")
    report = runner.run_price_ladder(build_sample_single_input(), [29.9, 39.9, 49.9, 59.9])

    json_path = output_dir / "price_ladder_report.json"
    md_path = output_dir / "price_ladder_report.md"

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(runner.render_price_ladder_markdown(report))

    print("Price ladder report generated.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
