import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ai_clients import AIClientConfig, OpenAICompatibleClient
from qualitative_research import QualitativeResearchInput, QualitativeResearchRunner


def _build_default_ai_client(base_dir: Path) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        config=AIClientConfig.from_env(base_dir=base_dir),
    )


def _schema_valid(report: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    research_plan = report.get("research_plan", {})
    required_plan_keys = {
        "task_breakdown",
        "research_objectives",
        "evaluation_dimensions",
        "sub_questions_for_personas",
        "required_information",
        "missing_information",
        "clarifying_questions",
        "ready_to_dispatch",
        "dispatch_scope",
        "target_personas",
        "planner_notes",
    }
    if set(research_plan.keys()) != required_plan_keys:
        return False

    summary = report.get("research_summary", {})
    summary_keys = {
        "consensus",
        "differences",
        "pain_points",
        "drivers",
        "barriers",
        "copy_insights",
        "recommendations",
    }
    if set(summary.keys()) != summary_keys:
        return False
    if any(not summary.get(key) for key in summary_keys):
        return False

    structured_recommendation = report.get("structured_recommendation", {})
    recommendation_keys = {
        "objective_answers",
        "cross_persona_consensus",
        "cross_persona_differences",
        "key_risks",
        "opportunity_areas",
        "recommended_actions",
        "copy_or_product_adjustments",
        "evidence_gaps",
        "confidence_assessment",
    }
    if set(structured_recommendation.keys()) != recommendation_keys:
        return False
    if any(not structured_recommendation.get(key) for key in recommendation_keys):
        return False

    consumer_voice = report.get("consumer_voice", [])
    if len(consumer_voice) != expected.get("agent_count", 0):
        return False

    meta = report.get("meta", {})
    if meta.get("mode") != expected.get("mode"):
        return False
    if meta.get("completion_status") != "complete":
        return False
    if meta.get("agent_count_expected") != expected.get("agent_count", 0):
        return False
    if meta.get("agent_count_completed") != expected.get("agent_count", 0):
        return False

    return True


def _persona_match(report: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    expected_persona_id = expected.get("persona_id")
    if not expected_persona_id:
        return True

    consumer_voice = report.get("consumer_voice", [])
    if len(consumer_voice) != 1:
        return False
    return consumer_voice[0].get("persona_id") == expected_persona_id


def _rate(success_count: int, total_count: int) -> float:
    if total_count == 0:
        return 0.0
    return round(success_count / total_count, 4)


def run_regression(
    golden_set_path: Path | str,
    output_path: Path | str,
    persona_path: Path | str,
    ai_client: Any | None = None,
) -> int:
    golden_set_path = Path(golden_set_path)
    output_path = Path(output_path)
    persona_path = Path(persona_path)
    base_dir = persona_path.resolve().parent
    active_ai_client = ai_client or _build_default_ai_client(base_dir)
    runner = QualitativeResearchRunner(persona_path, ai_client=active_ai_client)

    cases = json.loads(golden_set_path.read_text(encoding="utf-8"))
    case_results: List[Dict[str, Any]] = []

    completion_count = 0
    schema_valid_count = 0
    persona_match_count = 0

    for case in cases:
        expected = case.get("expected", {})
        try:
            report = runner.run(QualitativeResearchInput(**case["input"]))
            completed = report.get("meta", {}).get("completion_status") == "complete"
            schema_valid = _schema_valid(report, expected)
            persona_match = _persona_match(report, expected)
            error = ""
        except Exception as exc:
            report = {}
            completed = False
            schema_valid = False
            persona_match = False
            error = str(exc)

        completion_count += int(completed)
        schema_valid_count += int(schema_valid)
        persona_match_count += int(persona_match)

        case_results.append(
            {
                "id": case.get("id", ""),
                "completed": completed,
                "schema_valid": schema_valid,
                "persona_match": persona_match,
                "error": error,
                "report_meta": report.get("meta", {}),
            }
        )

    summary = {
        "case_count": len(cases),
        "completion_rate": _rate(completion_count, len(cases)),
        "schema_valid_rate": _rate(schema_valid_count, len(cases)),
        "persona_match_rate": _rate(persona_match_count, len(cases)),
    }
    summary["gate_passed"] = all(
        summary[key] == 1.0
        for key in ("completion_rate", "schema_valid_rate", "persona_match_rate")
    )

    payload = {
        "generated_at": datetime.now().isoformat(),
        "golden_set_path": str(golden_set_path),
        "summary": summary,
        "cases": case_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return 0 if summary["gate_passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden-set", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--persona-path",
        default="persona_samples_complete.json",
    )
    args = parser.parse_args()

    return run_regression(
        golden_set_path=args.golden_set,
        output_path=args.output,
        persona_path=args.persona_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
