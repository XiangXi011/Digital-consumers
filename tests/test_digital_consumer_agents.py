import json
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util
import sys


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class DigitalConsumerAgentTest(unittest.TestCase):
    """DigitalConsumerAgent 核心类测试"""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "digital_consumer_agents(1).py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_engine(self):
        if not self.module_path.exists():
            self.fail("digital_consumer_agents(1).py is missing")
        return load_module("digital_consumer_agents_under_test", self.module_path)

    def _make_agent(self, engine, **overrides):
        defaults = {
            "sample_id": "M01-01",
            "segment_id": "M01",
            "segment_name": "宠爱富养家",
            "subtype": "权威依赖型",
            "basic_profile": {
                "nickname": "苏梦瑶",
                "age": 35,
                "city": "深圳",
                "occupation": "医院副院长",
                "household_income_band": "120万-200万",
                "child_age_stage": "12岁",
            },
            "mindset_profile": {
                "decision_mode": "权威依赖",
                "openness_level": "low",
                "time_investment": "medium",
                "appearance_sensitivity": "medium",
                "price_sensitivity": "very_low",
            },
            "consumption_profile": {
                "core_needs": ["最高标准", "社交圈层匹配"],
                "preferred_channels": ["海外代购", "私立医院"],
                "trust_trigger": "医生推荐+专业背书",
                "rejection_trigger": "无医生背书",
                "budget_range": "60-100元/支",
            },
            "behavior_profile": {
                "content_habit": "高端母婴社群",
                "decision_style": "理性分析型",
            },
            "expression_profile": {
                "tone_style": "理性分析+权威口吻",
                "likely_quote": "牙医说用什么我就用什么",
            },
        }
        defaults.update(overrides)
        return engine.DigitalConsumerAgent(**defaults)

    def _make_product(self, engine, **overrides):
        defaults = {
            "name": "舒客儿童益生菌牙膏",
            "brand": "舒客",
            "category": "儿童口腔护理",
            "price": 39.9,
            "original_price": 59.9,
            "features": ["益生菌配方", "低氟防蛀"],
            "selling_points": ["医生推荐使用", "99%天然成分"],
            "packaging": {"attractive": True, "size": "60g"},
            "rating": 4.6,
            "sales_volume": 50000,
        }
        defaults.update(overrides)
        return engine.Product(**defaults)

    # ==================== 初始化测试 ====================

    def test_agent_initialization(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        self.assertEqual(agent.sample_id, "M01-01")
        self.assertEqual(agent.segment_id, "M01")
        self.assertEqual(agent.segment_name, "宠爱富养家")
        self.assertEqual(agent.current_state, "idle")
        self.assertEqual(agent.satisfaction, 0.5)

    def test_agent_memory_initialized(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        self.assertIn("current_product", agent.memory)
        self.assertIn("current_context", agent.memory)
        self.assertIn("recent_interactions", agent.memory)
        self.assertIsNone(agent.memory["current_product"])

    def test_agent_to_dict(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        d = agent.to_dict()
        self.assertEqual(d["sample_id"], "M01-01")
        self.assertEqual(d["segment_id"], "M01")
        self.assertIn("basic_profile", d)
        self.assertIn("mindset_profile", d)

    # ==================== 提示词生成测试 ====================

    def test_persona_prompt_contains_basic_info(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        prompt = agent.get_persona_prompt()
        self.assertIn("苏梦瑶", prompt)
        self.assertIn("35", prompt)
        self.assertIn("深圳", prompt)
        self.assertIn("医院副院长", prompt)

    def test_persona_prompt_contains_mindset(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        prompt = agent.get_persona_prompt()
        self.assertIn("权威依赖", prompt)

    def test_persona_prompt_contains_consumption(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        prompt = agent.get_persona_prompt()
        self.assertIn("医生推荐+专业背书", prompt)
        self.assertIn("60-100元/支", prompt)

    # ==================== 产品评估测试 ====================

    def test_evaluate_product_returns_required_keys(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        result = agent.evaluate_product(product)
        required_keys = [
            "agent_id", "agent_name", "segment", "product",
            "overall_score", "purchase_intention", "decision",
            "reasoning", "key_concerns", "preferred_features",
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_evaluate_product_score_range(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        result = agent.evaluate_product(product)
        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 10)

    def test_evaluate_product_intention_range(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        result = agent.evaluate_product(product)
        self.assertGreaterEqual(result["purchase_intention"], 0)
        self.assertLessEqual(result["purchase_intention"], 1.0)

    def test_evaluate_product_decision_values(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        result = agent.evaluate_product(product)
        valid_decisions = ["强烈购买", "考虑购买", "犹豫观望", "明确拒绝"]
        self.assertIn(result["decision"], valid_decisions)

    def test_evaluate_product_high_intention_decision(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, mindset_profile={
            "decision_mode": "自我主导",
            "openness_level": "high",
            "price_sensitivity": "low",
            "appearance_sensitivity": "high",
        }, consumption_profile={
            "core_needs": ["益生菌配方"],
            "preferred_channels": ["电商"],
            "trust_trigger": "医生推荐",
            "rejection_trigger": "",
            "budget_range": "0-100元/支",
        })
        product = self._make_product(engine, price=10.0)
        result = agent.evaluate_product(product)
        self.assertIn(result["decision"], ["强烈购买", "考虑购买"])

    def test_evaluate_product_low_intention_decision(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, consumption_profile={
            "core_needs": ["进口品质"],
            "preferred_channels": ["海外代购"],
            "trust_trigger": "进口品牌",
            "rejection_trigger": "国产",
            "budget_range": "0-10元/支",
        })
        product = self._make_product(engine, price=999.0)
        result = agent.evaluate_product(product)
        self.assertIn(result["decision"], ["犹豫观望", "明确拒绝"])

    def test_evaluate_product_updates_memory(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        agent.evaluate_product(product)
        self.assertIn("last_evaluation", agent.memory)

    def test_evaluate_product_updates_interaction_history(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        agent.evaluate_product(product)
        self.assertEqual(len(agent.interaction_history), 1)
        self.assertEqual(agent.interaction_history[0]["type"], "evaluation")

    # ==================== 价格评估测试 ====================

    def test_price_within_budget_returns_high_factor(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, consumption_profile={
            "core_needs": [],
            "preferred_channels": [],
            "trust_trigger": "",
            "rejection_trigger": "",
            "budget_range": "30-50元/支",
        })
        product = self._make_product(engine, price=35.0)
        result = agent.evaluate_product(product)
        self.assertGreaterEqual(result["price_evaluation"], 0.7)

    def test_price_above_budget_returns_low_factor(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, consumption_profile={
            "core_needs": [],
            "preferred_channels": [],
            "trust_trigger": "",
            "rejection_trigger": "",
            "budget_range": "10-20元/支",
        })
        product = self._make_product(engine, price=999.0)
        result = agent.evaluate_product(product)
        self.assertLess(result["price_evaluation"], 0.5)

    def test_price_sensitivity_adjusts_budget(self):
        engine = self.load_engine()
        high_sens = self._make_agent(engine, mindset_profile={
            "decision_mode": "价格敏感",
            "price_sensitivity": "high",
        }, consumption_profile={
            "core_needs": [],
            "preferred_channels": [],
            "trust_trigger": "",
            "rejection_trigger": "",
            "budget_range": "30-50元/支",
        })
        low_sens = self._make_agent(engine, sample_id="M01-02", mindset_profile={
            "decision_mode": "价格敏感",
            "price_sensitivity": "low",
        }, consumption_profile={
            "core_needs": [],
            "preferred_channels": [],
            "trust_trigger": "",
            "rejection_trigger": "",
            "budget_range": "30-50元/支",
        })
        product = self._make_product(engine, price=45.0)
        r_high = high_sens.evaluate_product(product)
        r_low = low_sens.evaluate_product(product)
        self.assertLess(r_high["price_evaluation"], r_low["price_evaluation"])

    # ==================== 行为模拟测试 ====================

    def test_simulate_behavior_returns_required_keys(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        result = agent.simulate_behavior(product)
        required_keys = ["agent_id", "agent_name", "product", "scenario",
                         "purchase_intention", "final_decision", "behavior_chain",
                         "estimated_conversion"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_simulate_behavior_chain_starts_with_browse(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        result = agent.simulate_behavior(product)
        self.assertGreater(len(result["behavior_chain"]), 0)
        self.assertEqual(result["behavior_chain"][0]["action"], "浏览")

    def test_simulate_behavior_high_intention_includes_purchase(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, consumption_profile={
            "core_needs": ["益生菌配方"],
            "preferred_channels": ["电商"],
            "trust_trigger": "医生推荐",
            "rejection_trigger": "",
            "budget_range": "0-100元/支",
        })
        product = self._make_product(engine, price=1.0)
        result = agent.simulate_behavior(product)
        actions = [b["action"] for b in result["behavior_chain"]]
        if result["purchase_intention"] > 0.7:
            self.assertIn("购买", actions)

    def test_simulate_behavior_promotion_scenario(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        normal = agent.simulate_behavior(product, scenario="normal")
        agent.reset_state()
        promo = agent.simulate_behavior(product, scenario="promotion")
        self.assertGreaterEqual(promo["purchase_intention"], normal["purchase_intention"] * 0.9)

    def test_simulate_behavior_social_scenario_for_social_follower(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, mindset_profile={
            "decision_mode": "社交跟随",
            "openness_level": "medium",
            "price_sensitivity": "medium",
        })
        product = self._make_product(engine)
        normal = agent.simulate_behavior(product, scenario="normal")
        agent.reset_state()
        social = agent.simulate_behavior(product, scenario="social")
        self.assertGreaterEqual(social["purchase_intention"], normal["purchase_intention"])

    # ==================== 讨论参与测试 ====================

    def test_participate_discussion_returns_required_keys(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        product = self._make_product(engine)
        agent.memory["current_product"] = product
        result = agent.participate_discussion("你会买吗？")
        required_keys = ["agent_id", "agent_name", "segment", "opinion", "response", "influence_level"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_social_follower_influenced_by_others(self):
        engine = self.load_engine()
        agent = self._make_agent(engine, mindset_profile={
            "decision_mode": "社交跟随",
            "openness_level": "medium",
            "price_sensitivity": "medium",
        })
        product = self._make_product(engine)
        agent.memory["current_product"] = product
        solo = agent.participate_discussion("你会买吗？")
        agent.reset_state()
        agent.memory["current_product"] = product
        others = [{"purchase_intention": 0.9}, {"purchase_intention": 0.95}]
        influenced = agent.participate_discussion("你会买吗？", other_opinions=others)
        self.assertGreater(influenced["opinion"]["purchase_intention"], solo["opinion"]["purchase_intention"] * 0.9)

    # ==================== 深度访谈测试 ====================

    def test_deep_interview_returns_responses(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        questions = ["你平时怎么选牙膏？", "你最担心什么？"]
        responses = agent.deep_interview(questions)
        self.assertEqual(len(responses), 2)
        for resp in responses:
            self.assertIn("question", resp)
            self.assertIn("answer", resp)
            self.assertIn("underlying_motivation", resp)
            self.assertIn("emotional_trigger", resp)

    def test_deep_interview_emotional_trigger_child(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        responses = agent.deep_interview(["你会给孩子买吗？"])
        self.assertIn("对孩子的关爱", responses[0]["emotional_trigger"])

    def test_deep_interview_emotional_trigger_safety(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        responses = agent.deep_interview(["你担心安全问题吗？"])
        self.assertIn("对健康的担忧", responses[0]["emotional_trigger"])

    # ==================== 状态重置测试 ====================

    def test_reset_state(self):
        engine = self.load_engine()
        agent = self._make_agent(engine)
        agent.satisfaction = 0.9
        agent.trust_level = 0.8
        agent.current_state = "active"
        agent.interaction_history = [{"type": "test"}]
        agent.reset_state()
        self.assertEqual(agent.satisfaction, 0.5)
        self.assertEqual(agent.trust_level, 0.5)
        self.assertEqual(agent.current_state, "idle")
        self.assertEqual(len(agent.interaction_history), 0)


class AgentOrchestratorTest(unittest.TestCase):
    """AgentOrchestrator 编排器测试"""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "digital_consumer_agents(1).py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_engine(self):
        if not self.module_path.exists():
            self.fail("digital_consumer_agents(1).py is missing")
        return load_module("digital_consumer_agents_under_test2", self.module_path)

    def _make_orchestrator(self, engine):
        agents = engine.load_agents_from_json(str(self.persona_path))
        orchestrator = engine.AgentOrchestrator()
        orchestrator.load_agents([a.to_dict() for a in agents])
        return orchestrator

    def _make_product(self, engine, **overrides):
        defaults = {
            "name": "舒客儿童益生菌牙膏",
            "brand": "舒客",
            "category": "儿童口腔护理",
            "price": 39.9,
            "features": ["益生菌配方", "低氟防蛀"],
            "selling_points": ["医生推荐使用"],
            "packaging": {"attractive": True},
            "rating": 4.6,
        }
        defaults.update(overrides)
        return engine.Product(**defaults)

    # ==================== 加载测试 ====================

    def test_load_agents_from_json(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        self.assertEqual(len(agents), 200)

    def test_orchestrator_loads_200_agents(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        self.assertEqual(len(orchestrator.agents), 200)

    def test_orchestrator_has_8_segments(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        self.assertEqual(len(orchestrator.segments), 8)

    def test_each_segment_has_25_agents(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        for segment_id, agent_ids in orchestrator.segments.items():
            self.assertEqual(len(agent_ids), 25, f"Segment {segment_id} has {len(agent_ids)} agents")

    # ==================== 第一层: 批量评估测试 ====================

    def test_batch_evaluate_returns_200_results(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product)
        self.assertEqual(len(results), 200)

    def test_batch_evaluate_with_segment_filter(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product, segment_filter="M01")
        self.assertEqual(len(results), 25)

    def test_batch_evaluate_invalid_segment_returns_all(self):
        """Invalid segment filter returns all agents (fallback behavior)"""
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product, segment_filter="INVALID")
        # Current behavior: invalid segment falls back to all agents
        self.assertEqual(len(results), 200)

    # ==================== 第二层: 小组讨论测试 ====================

    def test_select_representatives_stratified(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        selected = orchestrator.select_representatives(method="stratified", count=8)
        self.assertLessEqual(len(selected), 8)
        self.assertGreater(len(selected), 0)

    def test_select_representatives_random(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        selected = orchestrator.select_representatives(method="random", count=5)
        self.assertEqual(len(selected), 5)

    def test_select_representatives_with_segment_filter(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        selected = orchestrator.select_representatives(segment_id="M01", count=4)
        for agent_id in selected:
            self.assertTrue(agent_id.startswith("M01"))

    def test_group_discussion_returns_required_keys(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        participants = orchestrator.select_representatives(count=4)
        result = orchestrator.group_discussion("你会买吗？", product, participants)
        required_keys = ["topic", "product", "participants", "opinions", "consensus_level", "key_insights"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_group_discussion_consensus_range(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        participants = orchestrator.select_representatives(count=4)
        result = orchestrator.group_discussion("你会买吗？", product, participants)
        self.assertGreaterEqual(result["consensus_level"], 0)
        self.assertLessEqual(result["consensus_level"], 1.0)

    # ==================== 第三层: 深度追问测试 ====================

    def test_deep_dive_returns_required_keys(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        agent_id = list(orchestrator.agents.keys())[0]
        questions = ["你平时怎么选？", "你担心什么？"]
        result = orchestrator.deep_dive(agent_id, questions)
        required_keys = ["agent_id", "agent_name", "segment", "profile_summary", "interview_responses"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_deep_dive_invalid_agent(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        result = orchestrator.deep_dive("INVALID_ID", ["问题"])
        self.assertIn("error", result)

    # ==================== 报告生成测试 ====================

    def test_generate_report_returns_required_keys(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product)
        report = orchestrator.generate_report(results)
        required_keys = ["summary", "decision_distribution", "segment_analysis", "key_findings"]
        for key in required_keys:
            self.assertIn(key, report, f"Missing key: {key}")

    def test_generate_report_summary_fields(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product)
        report = orchestrator.generate_report(results)
        summary = report["summary"]
        self.assertEqual(summary["total_evaluated"], 200)
        self.assertIn("avg_score", summary)
        self.assertIn("avg_intention", summary)
        self.assertIn("estimated_conversion_rate", summary)

    def test_generate_report_decision_distribution_sums_to_200(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product)
        report = orchestrator.generate_report(results)
        total = sum(report["decision_distribution"].values())
        self.assertEqual(total, 200)

    def test_generate_report_segment_analysis_has_8_segments(self):
        engine = self.load_engine()
        orchestrator = self._make_orchestrator(engine)
        product = self._make_product(engine)
        results = orchestrator.batch_evaluate(product)
        report = orchestrator.generate_report(results)
        self.assertEqual(len(report["segment_analysis"]), 8)

    # ==================== 工具函数测试 ====================

    def test_create_sample_product(self):
        engine = self.load_engine()
        product = engine.create_sample_product()
        self.assertEqual(product.name, "舒客儿童益生菌牙膏")
        self.assertEqual(product.price, 39.9)
        self.assertIn("益生菌配方", product.features)


class IntegrationTest(unittest.TestCase):
    """端到端集成测试"""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "digital_consumer_agents(1).py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_engine(self):
        if not self.module_path.exists():
            self.fail("digital_consumer_agents(1).py is missing")
        return load_module("digital_consumer_agents_under_test3", self.module_path)

    def test_full_three_tier_workflow(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        orchestrator = engine.AgentOrchestrator()
        orchestrator.load_agents([a.to_dict() for a in agents])
        product = engine.create_sample_product()

        # Tier 1: Batch evaluation
        eval_results = orchestrator.batch_evaluate(product)
        self.assertEqual(len(eval_results), 200)

        # Tier 2: Group discussion
        representatives = orchestrator.select_representatives(method="stratified", count=8)
        discussion = orchestrator.group_discussion("你会买吗？", product, representatives)
        self.assertIn("consensus_level", discussion)

        # Tier 3: Deep dive
        deep_dive = orchestrator.deep_dive(
            representatives[0],
            ["你平时怎么选？", "你担心什么？"]
        )
        self.assertIn("interview_responses", deep_dive)

        # Generate report
        report = orchestrator.generate_report(eval_results)
        self.assertEqual(report["summary"]["total_evaluated"], 200)

    def test_multiple_products_comparison(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        orchestrator = engine.AgentOrchestrator()
        orchestrator.load_agents([a.to_dict() for a in agents])

        product_a = engine.Product(
            name="产品A", brand="品牌A", category="测试",
            price=29.9, features=["功能1"], selling_points=["卖点1"],
            rating=4.0,
        )
        product_b = engine.Product(
            name="产品B", brand="品牌B", category="测试",
            price=59.9, features=["功能2"], selling_points=["卖点2"],
            rating=4.8,
        )

        results_a = orchestrator.batch_evaluate(product_a)
        results_b = orchestrator.batch_evaluate(product_b)

        report_a = orchestrator.generate_report(results_a)
        report_b = orchestrator.generate_report(results_b)

        self.assertNotEqual(
            report_a["summary"]["avg_intention"],
            report_b["summary"]["avg_intention"],
        )

    def test_consistency_across_runs(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        orchestrator = engine.AgentOrchestrator()
        orchestrator.load_agents([a.to_dict() for a in agents])
        product = engine.create_sample_product()

        results1 = orchestrator.batch_evaluate(product)
        results2 = orchestrator.batch_evaluate(product)

        for r1, r2 in zip(results1, results2):
            self.assertEqual(r1["agent_id"], r2["agent_id"])
            self.assertEqual(r1["overall_score"], r2["overall_score"])
            self.assertEqual(r1["purchase_intention"], r2["purchase_intention"])
            self.assertEqual(r1["decision"], r2["decision"])


class BoundaryConditionTest(unittest.TestCase):
    """边界条件和异常处理测试"""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "digital_consumer_agents(1).py"

    def load_engine(self):
        if not self.module_path.exists():
            self.fail("digital_consumer_agents(1).py is missing")
        return load_module("digital_consumer_agents_under_test4", self.module_path)

    def test_agent_with_missing_profile_fields(self):
        engine = self.load_engine()
        agent = engine.DigitalConsumerAgent(
            sample_id="TEST-01",
            segment_id="TEST",
            segment_name="测试",
            subtype="测试",
        )
        product = engine.create_sample_product()
        result = agent.evaluate_product(product)
        self.assertIn("decision", result)

    def test_product_with_zero_price(self):
        engine = self.load_engine()
        agent = engine.DigitalConsumerAgent(
            sample_id="TEST-01", segment_id="TEST",
            segment_name="测试", subtype="测试",
            consumption_profile={"budget_range": "10-50元/支"},
        )
        product = engine.Product(
            name="免费产品", brand="测试", category="测试",
            price=0.0, features=[], selling_points=[],
        )
        result = agent.evaluate_product(product)
        self.assertEqual(result["price_evaluation"], 1.0)

    def test_product_with_very_high_price(self):
        engine = self.load_engine()
        agent = engine.DigitalConsumerAgent(
            sample_id="TEST-01", segment_id="TEST",
            segment_name="测试", subtype="测试",
            consumption_profile={"budget_range": "10-50元/支"},
        )
        product = engine.Product(
            name="超贵产品", brand="测试", category="测试",
            price=999999.0, features=[], selling_points=[],
        )
        result = agent.evaluate_product(product)
        self.assertLess(result["price_evaluation"], 0.5)

    def test_agent_with_invalid_budget_format(self):
        engine = self.load_engine()
        agent = engine.DigitalConsumerAgent(
            sample_id="TEST-01", segment_id="TEST",
            segment_name="测试", subtype="测试",
            consumption_profile={"budget_range": "invalid"},
        )
        product = engine.create_sample_product()
        result = agent.evaluate_product(product)
        self.assertIn("price_evaluation", result)

    def test_batch_simulate_with_sample_size(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.root / "persona_samples_complete.json"))
        orchestrator = engine.AgentOrchestrator()
        orchestrator.load_agents([a.to_dict() for a in agents])
        product = engine.create_sample_product()
        results = orchestrator.batch_simulate(product, sample_size=10)
        self.assertEqual(len(results), 10)

    def test_select_representatives_count_exceeds_available(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.root / "persona_samples_complete.json"))
        orchestrator = engine.AgentOrchestrator()
        orchestrator.load_agents([a.to_dict() for a in agents])
        selected = orchestrator.select_representatives(segment_id="M01", count=100)
        self.assertLessEqual(len(selected), 25)


class PersonaDataIntegrityTest(unittest.TestCase):
    """角色数据完整性测试"""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "digital_consumer_agents(1).py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_engine(self):
        if not self.module_path.exists():
            self.fail("digital_consumer_agents(1).py is missing")
        return load_module("digital_consumer_agents_under_test5", self.module_path)

    def test_all_agents_have_unique_ids(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        ids = [a.sample_id for a in agents]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_agents_have_valid_segments(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        valid_segments = {"M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08"}
        for agent in agents:
            self.assertIn(agent.segment_id, valid_segments, f"Invalid segment: {agent.segment_id}")

    def test_all_agents_have_required_profiles(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        for agent in agents:
            self.assertTrue(agent.basic_profile, f"Agent {agent.sample_id} missing basic_profile")
            self.assertTrue(agent.mindset_profile, f"Agent {agent.sample_id} missing mindset_profile")
            self.assertTrue(agent.consumption_profile, f"Agent {agent.sample_id} missing consumption_profile")

    def test_all_agents_have_nickname(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        for agent in agents:
            self.assertIn("nickname", agent.basic_profile, f"Agent {agent.sample_id} missing nickname")
            self.assertTrue(agent.basic_profile["nickname"], f"Agent {agent.sample_id} has empty nickname")

    def test_all_agents_have_decision_mode(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        for agent in agents:
            mode = agent.mindset_profile.get("decision_mode")
            self.assertIsNotNone(mode, f"Agent {agent.sample_id} missing decision_mode")
            self.assertTrue(len(mode) > 0, f"Agent {agent.sample_id} has empty decision_mode")

    def test_all_agents_have_budget_range(self):
        engine = self.load_engine()
        agents = engine.load_agents_from_json(str(self.persona_path))
        for agent in agents:
            budget = agent.consumption_profile.get("budget_range")
            self.assertTrue(budget, f"Agent {agent.sample_id} missing budget_range")


if __name__ == "__main__":
    unittest.main()
