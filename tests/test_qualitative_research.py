import importlib.util
import unittest
from pathlib import Path


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualitativeResearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "qualitative_research.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_or_fail(self):
        if not self.module_path.exists():
            self.fail("qualitative_research.py is missing")
        return load_module("qualitative_research_under_test", self.module_path)

    def test_multi_mode_returns_eight_mom_responses_and_summary(self):
        module = self.load_or_fail()
        runner = module.QualitativeResearchRunner(self.persona_path)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="8类妈妈会不会买，最大的顾虑是什么？",
                product_info="儿童牙膏，主打低氟防蛀和孩子更愿意坚持刷牙。",
            )
        )

        self.assertEqual(report["meta"]["mode"], "multi")
        self.assertEqual(report["meta"]["question_type"], "purchase_decision")
        self.assertEqual(report["meta"]["total_agents"], 8)
        self.assertEqual(len(report["consumer_voice"]), 8)
        self.assertEqual(
            sorted(report["research_summary"].keys()),
            [
                "barriers",
                "consensus",
                "copy_insights",
                "differences",
                "drivers",
                "pain_points",
                "recommendations",
            ],
        )
        self.assertIn("user_question", report["research_brief"])
        self.assertIn("product_info", report["research_brief"])

        first_response = report["consumer_voice"][0]
        self.assertEqual(
            sorted(first_response.keys()),
            [
                "concerns",
                "confidence_note",
                "core_needs",
                "decision_logic",
                "motivations",
                "persona_id",
                "persona_name",
                "question_type",
                "stance",
                "verbatim_answer",
            ],
        )

    def test_single_mode_returns_only_selected_persona(self):
        module = self.load_or_fail()
        runner = module.QualitativeResearchRunner(self.persona_path)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="高线忙碌妈会被哪句话打动？",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        self.assertEqual(report["meta"]["mode"], "single")
        self.assertEqual(report["meta"]["total_agents"], 1)
        self.assertEqual(len(report["consumer_voice"]), 1)
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M04")
        self.assertEqual(report["appendix"]["selected_persona"], "M04")
        self.assertTrue(report["research_summary"]["recommendations"])


if __name__ == "__main__":
    unittest.main()
