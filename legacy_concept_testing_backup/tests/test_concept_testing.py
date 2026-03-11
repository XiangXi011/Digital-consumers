import importlib.util
import unittest
from pathlib import Path


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SingleConceptTestingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "concept_testing.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_or_fail(self):
        if not self.module_path.exists():
            self.fail("concept_testing.py is missing")
        return load_module("concept_testing_under_test", self.module_path)

    def build_sample_input(self, module):
        return module.ConceptTestInput(
            concept_name="Shuke Kids Probiotic Toothpaste",
            brand="Shuke",
            category="Kids Oral Care",
            price=39.9,
            core_claims=["Probiotic formula", "Low fluoride cavity protection", "Kid-friendly taste"],
            packaging_summary="Cartoon fruit packaging with bright colors and clear age labeling.",
            tagline="A cavity-protection toothpaste kids will actually enjoy using.",
            target_channels=["Tmall", "JD", "Mother & Baby Stores"],
            competitive_anchors=["Oral-B Kids", "Putzi"],
            context_notes="Used for early concept validation before external research.",
        )

    def test_concept_input_maps_to_product(self):
        module = self.load_or_fail()
        concept = self.build_sample_input(module)

        product = concept.to_product()

        self.assertEqual(product.name, concept.concept_name)
        self.assertEqual(product.brand, concept.brand)
        self.assertEqual(product.category, concept.category)
        self.assertEqual(product.price, concept.price)
        self.assertEqual(product.features, concept.core_claims)
        self.assertIn(concept.tagline, product.selling_points)
        self.assertEqual(product.packaging["summary"], concept.packaging_summary)

    def test_runner_generates_full_report_sections(self):
        module = self.load_or_fail()
        runner = module.ConceptTestRunner(self.persona_path)
        report = runner.run(self.build_sample_input(module))

        self.assertEqual(report["meta"]["total_personas"], 200)
        self.assertIn("executive_summary", report)
        self.assertIn("purchase_intent", report)
        self.assertIn("segment_opportunity", report)
        self.assertIn("reasons_to_buy", report)
        self.assertIn("barriers", report)
        self.assertIn("voice_of_consumer", report)
        self.assertIn("optimization_suggestions", report)
        self.assertIn("appendix", report)

    def test_runner_generates_business_report_fields(self):
        module = self.load_or_fail()
        runner = module.ConceptTestRunner(self.persona_path)
        report = runner.run(self.build_sample_input(module))

        self.assertIn("business_recommendation", report["executive_summary"])
        self.assertIn("confidence_level", report["executive_summary"])
        self.assertIn("confidence_reason", report["executive_summary"])
        self.assertNotIn(
            report["executive_summary"]["business_recommendation"],
            {"advance_to_real_research", "revise_then_retest", "do_not_advance_yet"},
        )
        self.assertIn("diagnosis", report)
        self.assertIn("decision_drivers", report["diagnosis"])
        self.assertIn("value_proposition_conflicts", report["diagnosis"])
        self.assertIn("competitive_limitations", report["diagnosis"])
        self.assertIn("action_plan", report)
        self.assertIn("immediate_actions", report["action_plan"])
        self.assertIn("next_round_prerequisites", report["action_plan"])
        self.assertIn("recommended_next_tests", report["action_plan"])
        self.assertIn("report_boundary", report)
        self.assertIn("input_completeness", report["report_boundary"])
        self.assertIn("credibility_notes", report["report_boundary"])
        self.assertIn("why_high_or_low", report["segment_opportunity"]["top_segments"][0])
        self.assertIn("top_reason_tag", report["segment_opportunity"]["top_segments"][0])

    def test_voice_of_consumer_entries_include_stance_and_reason_tag(self):
        module = self.load_or_fail()
        runner = module.ConceptTestRunner(self.persona_path)

        evaluation_results = [
            {
                "agent_id": "a1",
                "agent_name": "支持者甲",
                "segment": "宠爱富养家",
                "purchase_intention": 0.78,
                "decision": "强烈购买",
                "reasoning": "功能利益点足够清晰",
                "key_concerns": [],
                "preferred_features": ["趣味刷牙监督"],
            },
            {
                "agent_id": "a2",
                "agent_name": "犹豫者乙",
                "segment": "全能优等家",
                "purchase_intention": 0.46,
                "decision": "犹豫观望",
                "reasoning": "我还想确认一下安全证明",
                "key_concerns": ["担心成分安全性"],
                "preferred_features": ["魔法变色过程"],
            },
            {
                "agent_id": "a3",
                "agent_name": "拒绝者丙",
                "segment": "传统关爱妈",
                "purchase_intention": 0.12,
                "decision": "明确拒绝",
                "reasoning": "我更想要稳妥防蛀，不想要太花哨",
                "key_concerns": ["担心概念太花哨"],
                "preferred_features": [],
            },
        ]
        discussion = {
            "opinions": [
                {
                    "agent_id": "a1",
                    "agent_name": "支持者甲",
                    "segment": "宠爱富养家",
                    "response": "[支持者甲] 我再看看",
                    "opinion": {"purchase_intention": 0.78, "decision": "强烈购买"},
                },
                {
                    "agent_id": "a2",
                    "agent_name": "犹豫者乙",
                    "segment": "全能优等家",
                    "response": "[犹豫者乙] 这个包装太好看了，小红书刷到就下单了",
                    "opinion": {"purchase_intention": 0.46, "decision": "犹豫观望"},
                },
                {
                    "agent_id": "a3",
                    "agent_name": "拒绝者丙",
                    "segment": "传统关爱妈",
                    "response": "[拒绝者丙] 这个看着高级，送人也有面子",
                    "opinion": {"purchase_intention": 0.12, "decision": "明确拒绝"},
                },
            ]
        }

        voice = runner._build_voice_of_consumer(evaluation_results, discussion, deep_dives={})

        self.assertEqual(voice["supporters"][0]["stance_label"], "支持者")
        self.assertEqual(voice["hesitant"][0]["stance_label"], "犹豫者")
        self.assertEqual(voice["rejecting"][0]["stance_label"], "拒绝者")
        self.assertTrue(voice["supporters"][0]["reason_tag"])
        self.assertTrue(voice["hesitant"][0]["reason_tag"])
        self.assertTrue(voice["rejecting"][0]["reason_tag"])
        self.assertNotEqual(voice["rejecting"][0]["quote"], "[拒绝者丙] 这个看着高级，送人也有面子")

    def test_voice_entry_uses_llm_quote_when_validation_passes(self):
        module = self.load_or_fail()

        class StubAIClient:
            def generate_consumer_quote(self, payload):
                return {"mode": "live_quote", "quote": "孩子可能会喜欢这个过程，我愿意先试试。"}

            def validate_consumer_quote(self, expected_stance, expected_reason_tag, quote):
                return {
                    "mode": "live_validation",
                    "is_consistent": True,
                    "detected_stance": expected_stance,
                    "detected_reason": expected_reason_tag,
                    "why": "stance aligned",
                }

        runner = module.ConceptTestRunner(self.persona_path, ai_client=StubAIClient())
        entry = runner._build_voice_entry(
            evaluation={
                "agent_id": "a1",
                "agent_name": "支持者甲",
                "segment": "宠爱富养家",
                "purchase_intention": 0.71,
                "decision": "强烈购买",
                "reasoning": "这个卖点比较有吸引力",
                "key_concerns": [],
                "preferred_features": ["趣味刷牙监督"],
            },
            stance_label="支持者",
            discussion_entry=None,
            deep_dive_entry=None,
        )

        self.assertEqual(entry["quote"], "孩子可能会喜欢这个过程，我愿意先试试。")
        self.assertEqual(entry["quote_generation_mode"], "live_quote")
        self.assertTrue(entry["quote_validation"]["is_consistent"])

    def test_voice_entry_falls_back_when_validation_fails(self):
        module = self.load_or_fail()

        class StubAIClient:
            def generate_consumer_quote(self, payload):
                return {"mode": "live_quote", "quote": "这个包装太好看了，我直接就想下单。"}

            def validate_consumer_quote(self, expected_stance, expected_reason_tag, quote):
                return {
                    "mode": "live_validation",
                    "is_consistent": False,
                    "detected_stance": "支持者",
                    "detected_reason": "包装吸引力",
                    "why": "quote sounds supportive",
                }

        runner = module.ConceptTestRunner(self.persona_path, ai_client=StubAIClient())
        entry = runner._build_voice_entry(
            evaluation={
                "agent_id": "a2",
                "agent_name": "拒绝者乙",
                "segment": "传统关爱妈",
                "purchase_intention": 0.12,
                "decision": "明确拒绝",
                "reasoning": "我更想要稳妥防蛀，不想要太花哨",
                "key_concerns": ["担心概念太花哨"],
                "preferred_features": [],
            },
            stance_label="拒绝者",
            discussion_entry=None,
            deep_dive_entry=None,
        )

        self.assertEqual(entry["quote_generation_mode"], "fallback_rule_after_validation")
        self.assertFalse(entry["quote_validation"]["is_consistent"])
        self.assertIn("暂时不会买", entry["quote"])

    def test_voice_entry_falls_back_when_llm_generation_errors(self):
        module = self.load_or_fail()

        class StubAIClient:
            def generate_consumer_quote(self, payload):
                raise RuntimeError("quote generation failed")

            def validate_consumer_quote(self, expected_stance, expected_reason_tag, quote):
                raise AssertionError("validation should not be called when generation fails")

        runner = module.ConceptTestRunner(self.persona_path, ai_client=StubAIClient())
        entry = runner._build_voice_entry(
            evaluation={
                "agent_id": "a3",
                "agent_name": "犹豫者丙",
                "segment": "高线忙碌派",
                "purchase_intention": 0.42,
                "decision": "犹豫观望",
                "reasoning": "我还想确认一下安全证明",
                "key_concerns": ["担心成分安全性"],
                "preferred_features": ["魔法变色过程"],
            },
            stance_label="犹豫者",
            discussion_entry=None,
            deep_dive_entry=None,
        )

        self.assertEqual(entry["quote_generation_mode"], "fallback_rule_error")
        self.assertIn("还缺一点让我放心下单", entry["quote"])
        self.assertEqual(entry["quote_validation"]["mode"], "skipped_after_generation_error")

    def test_runner_is_backed_by_langgraph_analysis_graph(self):
        module = self.load_or_fail()

        self.assertTrue(hasattr(module, "build_analysis_graph"))

        runner = module.ConceptTestRunner(self.persona_path)
        self.assertTrue(hasattr(runner, "analysis_graph"))
        self.assertIsNotNone(runner.analysis_graph)

    def test_discussion_selection_covers_all_segments(self):
        module = self.load_or_fail()
        runner = module.ConceptTestRunner(self.persona_path)
        concept = self.build_sample_input(module)
        evaluation_results = runner.run_batch_evaluation(concept.to_product())

        participant_ids = runner.select_discussion_participants(evaluation_results)
        participant_segments = {
            runner.orchestrator.agents[agent_id].segment_id for agent_id in participant_ids
        }

        self.assertEqual(len(participant_ids), 8)
        self.assertEqual(len(participant_segments), 8)

    def test_deep_dive_selection_uses_expected_buckets(self):
        module = self.load_or_fail()
        runner = module.ConceptTestRunner(self.persona_path)
        concept = self.build_sample_input(module)
        evaluation_results = runner.run_batch_evaluation(concept.to_product())

        selected = runner.select_deep_dive_candidates(evaluation_results)

        self.assertEqual(len(selected["high_intent"]), 2)
        self.assertEqual(len(selected["hesitant"]), 2)
        self.assertEqual(len(selected["rejecting"]), 2)

    def test_markdown_report_contains_business_sections(self):
        module = self.load_or_fail()
        runner = module.ConceptTestRunner(self.persona_path)
        report = runner.run(self.build_sample_input(module))

        markdown = runner.render_markdown_report(report)

        self.assertIn("# Single Concept Test Report", markdown)
        self.assertIn("## Executive Summary", markdown)
        self.assertIn("## Decision Drivers", markdown)
        self.assertIn("## Purchase Intent", markdown)
        self.assertIn("## Segment Opportunity", markdown)
        self.assertIn("## Consumer Voice", markdown)
        self.assertIn("## Action Plan", markdown)
        self.assertIn("## Report Boundary", markdown)


if __name__ == "__main__":
    unittest.main()
