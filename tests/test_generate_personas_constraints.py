import importlib.util
import unittest
from pathlib import Path

import yaml


ORDINAL_FIELDS = {
    "openness_level": ["low", "medium", "high"],
    "time_investment": ["very_low", "low", "medium", "high", "very_high"],
    "appearance_sensitivity": ["very_low", "low", "medium", "high", "very_high"],
    "evidence_sensitivity": ["very_low", "low", "medium", "high", "very_high"],
    "trend_sensitivity": ["very_low", "low", "medium", "high", "very_high"],
    "price_sensitivity": ["very_low", "low", "medium", "high", "very_high"],
    "switching_willingness": ["very_low", "low", "medium", "high", "very_high"],
}


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PersonaGenerationConstraintsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.generator = load_module(
            "generate_personas_under_test",
            next(cls.root.glob("generate_personas*.py")),
        )
        with open(next(cls.root.glob("persona_generation_rules*.yaml")), "r", encoding="utf-8") as handle:
            cls.segment_rules = yaml.safe_load(handle)

    def generate_samples(self):
        self.generator.random.seed(42)
        return self.generator.generate_all_personas()

    def test_demographic_and_subtype_hard_constraints_hold(self):
        samples = self.generate_samples()
        failures = []

        for sample in samples:
            segment_id = sample["segment_id"]
            config = self.generator.SEGMENT_CONFIG[segment_id]
            subtype = sample["subtype"]
            subtype_features = self.generator.SUBTYPE_FEATURES[subtype]
            basic = sample["basic_profile"]
            consumption = sample["consumption_profile"]
            expression = sample["expression_profile"]

            checks = {
                "age": config["age_range"][0] <= basic["age"] <= config["age_range"][1],
                "city": basic["city"] in config["cities"],
                "district": basic["district"] in config["cities"][basic["city"]],
                "occupation": basic["occupation"] in config["occupations"],
                "income": basic["household_income_band"] in config["income_bands"],
                "family_structure": basic["family_structure"] in config["family_structures"],
                "child_age": basic["child_age_stage"] in config["child_ages"],
                "budget": consumption["budget_range"] == config["budget"],
                "decision_mode": sample["mindset_profile"]["decision_mode"] == subtype_features["decision_mode"],
                "trust_trigger": consumption["trust_trigger"] == subtype_features["trust_trigger"],
                "rejection_trigger": consumption["rejection_trigger"] == subtype_features["rejection_trigger"],
                "tone_style": expression["tone_style"] == subtype_features["tone"],
                "quote": expression["likely_quote"] == subtype_features["quote"],
                "review_focus": sample["review_focus"] == subtype_features["review_focus"],
            }

            for field_name, passed in checks.items():
                if not passed:
                    failures.append((sample["sample_id"], field_name))

        self.assertFalse(failures, f"Hard constraints failed for samples: {failures[:10]}")

    def test_segment_whitelist_fields_stay_inside_segment_boundaries(self):
        samples = self.generate_samples()
        failures = []

        for sample in samples:
            rules = self.segment_rules[sample["segment_id"]]
            consumption = sample["consumption_profile"]
            behavior = sample["behavior_profile"]

            for need in consumption["core_needs"]:
                if need not in rules["core_needs_options"]:
                    failures.append((sample["sample_id"], "core_needs", need))

            for channel in consumption["preferred_channels"]:
                if channel not in rules["preferred_channels"]:
                    failures.append((sample["sample_id"], "preferred_channels", channel))

            if behavior["content_habit"] not in rules["content_habits"]:
                failures.append((sample["sample_id"], "content_habit", behavior["content_habit"]))

            if behavior["decision_style"] not in rules["decision_styles"]:
                failures.append((sample["sample_id"], "decision_style", behavior["decision_style"]))

            if behavior["family_role"] not in rules["family_roles"]:
                failures.append((sample["sample_id"], "family_role", behavior["family_role"]))

        self.assertFalse(failures, f"Segment whitelist failures: {failures[:10]}")

    def test_constrained_random_fields_stay_within_one_step_of_segment_center(self):
        samples = self.generate_samples()
        failures = []

        for sample in samples:
            rules = self.segment_rules[sample["segment_id"]]
            mindset = sample["mindset_profile"]
            behavior = sample["behavior_profile"]

            for field_name, scale in ORDINAL_FIELDS.items():
                sample_value = behavior[field_name] if field_name == "switching_willingness" else mindset[field_name]
                rule_value = rules[field_name]
                distance = abs(scale.index(sample_value) - scale.index(rule_value))

                if distance > 1:
                    failures.append((sample["sample_id"], field_name, sample_value, rule_value))

        self.assertFalse(
            failures,
            f"Constrained random fields exceeded one-step boundary: {failures[:10]}",
        )


if __name__ == "__main__":
    unittest.main()
