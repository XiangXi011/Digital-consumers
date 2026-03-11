import json
from pathlib import Path

from html_report_renderer import HTMLReportRenderer
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


def build_sample_research_request() -> QualitativeResearchInput:
    return QualitativeResearchInput(
        mode="multi",
        question_type="purchase_decision",
        user_question="这款儿童牙膏 8 类妈妈会不会买，最大的顾虑是什么？",
        product_info="低氟防蛀，孩子更愿意坚持刷牙。",
        copy_material="专业防蛀，孩子喜欢，妈妈省心。",
        background_material="用于上市前的定性预研究。",
    )


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = QualitativeResearchRunner(base_dir / "persona_samples_complete.json")
    report = runner.run(build_sample_research_request())
    html = HTMLReportRenderer().render(report)

    json_path = output_dir / "qualitative_research_report.json"
    html_path = output_dir / "qualitative_research_report.html"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    print("Qualitative research report generated.")
    print(f"JSON: {json_path}")
    print(f"HTML: {html_path}")


if __name__ == "__main__":
    main()
