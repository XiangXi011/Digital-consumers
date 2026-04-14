import importlib.util
import json
import unittest
from pathlib import Path


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StubAIClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.is_configured = True

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        if not self.responses:
            raise AssertionError("StubAIClient ran out of responses")
        return self.responses.pop(0)


def planner_json(
    *,
    ready_to_dispatch: bool,
    dispatch_scope: str,
    target_personas: list[str],
    missing_information: list[str] | None = None,
    clarifying_questions: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "task_breakdown": ["判断用户核心问题", "验证主要购买障碍"],
            "research_objectives": ["判断是否愿意购买", "定位主要障碍和打动点"],
            "evaluation_dimensions": ["信任", "价格", "效果理解"],
            "sub_questions_for_personas": ["你会不会买", "你最大的顾虑是什么"],
            "required_information": ["用户问题", "产品信息或文案"],
            "missing_information": missing_information or [],
            "clarifying_questions": clarifying_questions or [],
            "ready_to_dispatch": ready_to_dispatch,
            "dispatch_scope": dispatch_scope,
            "target_personas": target_personas,
            "planner_notes": ["先围绕信任与效果理解收集反馈"],
        },
        ensure_ascii=False,
    )


def mom_json(persona_id: str) -> str:
    return json.dumps(
        {
            "persona_id": persona_id,
            "persona_name": f"{persona_id}-mom",
            "task_responses": [
                {"question": "你会不会买", "answer": "如果证据清楚我会尝试"},
                {"question": "你最大的顾虑是什么", "answer": "怕说得太笼统"},
            ],
            "dimension_scores": [
                {"dimension": "信任", "judgement": "需要更强证据"},
                {"dimension": "效果理解", "judgement": "卖点还不够具体"},
            ],
            "stance": "interested",
            "efficacy_clarity": 4,
            "trust_signal": 3,
            "convenience": 4,
            "price_fit": 3,
            # Include rubric_scores for all known task-type dimensions
            "rubric_scores": {
                # concept_test
                "demand_fit": 4, "differentiation": 3, "purchase_drive": 4, "price_acceptance": 3,
                # packaging_review
                "shelf_recognition": 4, "info_clarity": 3, "visual_trust": 3, "pickup_willingness": 4,
                # copy_feedback
                "memory_strength": 4, "credibility": 3, "conversion_power": 3, "emotional_resonance": 4,
                # ab_test
                "option_a_alignment": 4, "option_b_alignment": 3, "overall_preference": 3, "switching_cost": 3,
                # price_test
                "price_sensitivity": 3, "value_perception": 4, "competitive_position": 3, "purchase_willingness": 4,
            },
            "triggered_veto_codes": [],
            "core_needs": ["安全可靠", "省心"],
            "motivations": ["专业背书", "孩子愿意接受"],
            "concerns": ["价格是否合理"],
            "decision_logic": "先看证据，再判断是否值得尝试。",
            "verbatim_answer": "如果证据充分，我愿意试试。",
            "evidence_trace": "重视专业背书和孩子接受度。",
        },
        ensure_ascii=False,
    )


def synthesis_json() -> str:
    return json.dumps(
        {
            "research_summary": {
                "consensus": ["大多数妈妈先看可信证据。"],
                "differences": ["价格敏感度存在差异。"],
                "pain_points": ["担心效果说不清。"],
                "drivers": ["专业证明和孩子接受度。"],
                "barriers": ["价格和信任门槛。"],
                "copy_insights": ["先讲核心利益，再给证明。"],
                "recommendations": ["收敛单一卖点并补证据。"],
            },
            "structured_recommendation": {
                "objective_answers": ["妈妈会先验证可信度，再考虑购买。"],
                "cross_persona_consensus": ["信任和效果理解最关键。"],
                "cross_persona_differences": ["部分人群更看重价格。"],
                "key_risks": ["证据不足会直接抬高怀疑。"],
                "opportunity_areas": ["用更具体的结果证明建立信任。"],
                "recommended_actions": ["重写首屏卖点并补充可验证证据。"],
                "copy_or_product_adjustments": ["弱化空泛表达，强化专业证明。"],
                "evidence_gaps": ["缺真实用户体验或实验依据。"],
                "confidence_assessment": ["结论方向明确，但证据仍需加强。"],
            },
        },
        ensure_ascii=False,
    )


def incomplete_error_type(module):
    return getattr(module, "IncompleteResearchRunError", RuntimeError)


def planner_blocked_error_type(module):
    return getattr(module, "ResearchPlannerBlockedError", RuntimeError)


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

    def test_multi_mode_report_contains_research_plan_and_structured_recommendation(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="multi",
                        target_personas=[f"M0{index}" for index in range(1, 9)],
                    ),
                },
                *[{"mode": "live_text", "text": mom_json(f"M0{index}")} for index in range(1, 9)],
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="8类妈妈会不会买，最大的顾虑是什么？",
                product_info="儿童牙膏，主打低氟防蛀和孩子更愿意坚持刷牙。",
            )
        )

        self.assertEqual(len(ai_client.calls), 10)
        self.assertEqual(report["meta"]["mode"], "multi")
        self.assertEqual(report["meta"]["total_agents"], 8)
        self.assertEqual(report["meta"]["agent_count_expected"], 8)
        self.assertEqual(report["meta"]["agent_count_completed"], 8)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertIn("research_plan", report)
        self.assertIn("structured_recommendation", report)
        self.assertTrue(report["research_plan"]["ready_to_dispatch"])
        self.assertEqual(
            sorted(report["structured_recommendation"].keys()),
            [
                "confidence_assessment",
                "copy_or_product_adjustments",
                "cross_persona_consensus",
                "cross_persona_differences",
                "evidence_gaps",
                "key_risks",
                "objective_answers",
                "opportunity_areas",
                "recommended_actions",
            ],
        )

    def test_planner_runs_before_mother_agents_and_task_card_reaches_mother_prompt(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="高线忙碌妈妈会被哪句话打动？",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        self.assertIn("planner", (ai_client.calls[0]["system_prompt"] or "").lower())
        self.assertIn("判断用户核心问题", ai_client.calls[1]["prompt"])
        self.assertIn("信任", ai_client.calls[1]["prompt"])

    def test_mom_payload_preserves_voice_line_and_confidence_note(self):
        module = self.load_or_fail()
        payload = json.loads(mom_json("M04"))
        payload["voice_line"] = "太麻烦我就不会继续看了。"
        payload["confidence_note"] = "只基于现有卖点，判断还不够稳。"

        validated = module._validate_mom_payload(payload, "M04", "copy_feedback")

        self.assertEqual(validated["voice_line"], "太麻烦我就不会继续看了。")
        self.assertEqual(validated["confidence_note"], "只基于现有卖点，判断还不够稳。")

    def test_planner_blocks_execution_and_returns_clarification_request(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=False,
                        dispatch_scope="multi",
                        target_personas=[f"M0{index}" for index in range(1, 9)],
                        missing_information=["产品信息"],
                        clarifying_questions=["请补充产品信息或核心卖点。"],
                    ),
                }
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        with self.assertRaises(planner_blocked_error_type(module)) as context:
            runner.run(
                module.QualitativeResearchInput(
                    mode="multi",
                    question_type="purchase_decision",
                    user_question="8类妈妈会不会买？",
                )
            )

        self.assertEqual(len(ai_client.calls), 1)
        self.assertIn("产品信息", str(context.exception))

    def test_planner_normalizes_builtin_eight_mom_pack_without_reasking_segment_definition(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=False,
                        dispatch_scope="multi",
                        target_personas=["待定：需要等待8类妈妈定义"],
                        missing_information=["8类妈妈画像的具体定义"],
                        clarifying_questions=["请明确8类妈妈具体指哪8类细分人群？"],
                    ),
                }
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        plan = runner.plan(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="8类妈妈会不会买这款儿童牙膏？",
                product_info="低氟防蛀儿童牙膏",
                persona_pack_id="default-eight-moms-v1",
                audience_segments=[
                    "M01 宠爱富养家",
                    "M02 自在成长家",
                    "M03 传统关爱妈",
                    "M04 高线忙碌派",
                    "M05 品质精算师",
                    "M06 小镇贵妇妈",
                    "M07 全能优等家",
                    "M08 佛系粗养家",
                ],
            )
        )

        self.assertTrue(plan["ready_to_dispatch"])
        self.assertEqual(plan["dispatch_scope"], "multi")
        self.assertEqual(plan["target_personas"], [f"M0{index}" for index in range(1, 9)])
        self.assertEqual(plan["missing_information"], [])
        self.assertEqual(plan["clarifying_questions"], [])
        self.assertIn("default-eight-moms-v1", ai_client.calls[0]["prompt"])

    def test_single_mode_uses_planner_selected_persona_only(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="高线忙碌妈妈会被哪句话打动？",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        self.assertEqual(len(ai_client.calls), 3)
        self.assertEqual(report["meta"]["mode"], "single")
        self.assertEqual(report["meta"]["total_agents"], 1)
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M04")
        self.assertEqual(report["research_plan"]["target_personas"], ["M04"])

    def test_explicit_single_persona_request_overrides_planner_scope_drift(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="multi",
                        target_personas=[f"M0{index}" for index in range(1, 9)],
                    ),
                },
                *[{"mode": "live_text", "text": mom_json(f"M0{index}")} for index in range(1, 9)],
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="高线忙碌妈妈会被哪句文案打动？",
                copy_material="专业防蛀，孩子更爱刷牙，妈妈更省心。",
            )
        )

        self.assertEqual(report["meta"]["mode"], "single")
        self.assertEqual(report["meta"]["total_agents"], 1)
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M04")
        self.assertEqual(report["research_plan"]["dispatch_scope"], "single")
        self.assertEqual(report["research_plan"]["target_personas"], ["M04"])

    def test_planner_normalizes_alias_fields_and_scalar_values(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": json.dumps(
                        {
                            "task_breakdown": "decide whether the concept is runnable",
                            "research_goals": "understand purchase intent",
                            "evaluation_dimensions": "trust",
                            "sub_questions": [
                                "would you buy it",
                                "what is the main concern",
                            ],
                            "required_info": "user question and product info",
                            "missing_info": [],
                            "clarification_questions": [],
                            "ready_to_dispatch": "true",
                            "dispatch_scope": "multi",
                            "planner_notes": "normalized from alias payload",
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        plan = runner.plan(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="Will mothers buy this toothpaste?",
                product_info="Low-fluoride kids toothpaste.",
            )
        )

        self.assertEqual(plan["task_breakdown"], ["decide whether the concept is runnable"])
        self.assertEqual(plan["research_objectives"], ["understand purchase intent"])
        self.assertEqual(plan["evaluation_dimensions"], ["trust"])
        self.assertEqual(
            plan["sub_questions_for_personas"],
            ["would you buy it", "what is the main concern"],
        )
        self.assertEqual(plan["required_information"], ["user question and product info"])
        self.assertTrue(plan["ready_to_dispatch"])
        self.assertEqual(plan["dispatch_scope"], "multi")
        self.assertEqual(len(plan["target_personas"]), 8)
        self.assertIn("normalized from alias payload", plan["planner_notes"][0])

    def test_planner_normalizes_object_research_objectives_into_list(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": json.dumps(
                        {
                            "task_breakdown": [
                                "define the 8 mom segments",
                                "measure purchase intent",
                            ],
                            "research_objectives": {
                                "primary": "measure segment-level purchase intent",
                                "secondary": "identify the biggest objections",
                            },
                            "evaluation_dimensions": ["trust", "safety", "price"],
                            "sub_questions_for_personas": [
                                "would you buy it",
                                "what is your biggest concern",
                            ],
                            "required_information": ["user_question", "product_info"],
                            "missing_information": [],
                            "clarifying_questions": [],
                            "ready_to_dispatch": True,
                            "dispatch_scope": "multi",
                            "target_personas": [f"M0{index}" for index in range(1, 9)],
                            "planner_notes": ["object payload from planner"],
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        plan = runner.plan(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="Will the 8 mom segments buy this toothpaste?",
                product_info="Low-fluoride kids toothpaste.",
            )
        )

        self.assertEqual(
            plan["research_objectives"],
            [
                "measure segment-level purchase intent",
                "identify the biggest objections",
            ],
        )

    def test_planner_retries_when_ai_client_temporarily_returns_fallback_text(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "fallback_text",
                    "text": "Fallback summary: remote text generation failed.",
                    "errors": ["primary model timeout"],
                },
                {
                    "mode": "fallback_text",
                    "text": "Fallback summary: remote text generation failed again.",
                    "errors": ["fallback model timeout"],
                },
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="multi",
                        target_personas=[f"M0{index}" for index in range(1, 9)],
                    ),
                },
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        plan = runner.plan(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="Will mothers buy this toothpaste?",
                product_info="Low-fluoride kids toothpaste.",
            )
        )

        self.assertTrue(plan["ready_to_dispatch"])
        self.assertEqual(len(ai_client.calls), 3)

    def test_planner_falls_back_when_present_fields_normalize_to_empty_values(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": json.dumps(
                        {
                            "task_breakdown": [
                                "define the 8 mom segments",
                                "measure purchase intent and concerns",
                            ],
                            "research_objectives": {
                                "primary": "validate purchase intent",
                                "secondary": "find the biggest concern",
                            },
                            "evaluation_dimensions": [
                                "purchase intent",
                                "trust",
                                "barriers",
                            ],
                            "sub_questions_for_personas": {"待明确": ""},
                            "required_information": ["user_question", "product_info"],
                            "missing_information": [],
                            "clarifying_questions": [],
                            "ready_to_dispatch": True,
                            "dispatch_scope": None,
                            "target_personas": [],
                            "planner_notes": "planner returned sparse sub-questions",
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        plan = runner.plan(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="Will the 8 mom segments buy this toothpaste?",
                product_info="Low-fluoride kids toothpaste.",
            )
        )

        self.assertEqual(
            plan["sub_questions_for_personas"],
            ["Will the 8 mom segments buy this toothpaste?"],
        )
        self.assertEqual(plan["dispatch_scope"], "multi")
        self.assertEqual(len(plan["target_personas"]), 8)

    def test_runner_retries_when_persona_temporarily_returns_fallback_text(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {
                    "mode": "fallback_text",
                    "text": "Fallback summary: remote text generation failed.",
                    "errors": ["persona primary model timeout"],
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="Will this copy persuade a busy mother?",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        self.assertEqual(report["meta"]["total_agents"], 1)
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M04")
        self.assertEqual(len(ai_client.calls), 4)

    def test_runner_retries_when_synthesizer_temporarily_returns_fallback_text(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {
                    "mode": "fallback_text",
                    "text": "Fallback summary: remote text generation failed.",
                    "errors": ["synth primary model timeout"],
                },
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="Will this copy persuade a busy mother?",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        self.assertEqual(report["meta"]["total_agents"], 1)
        self.assertEqual(report["consumer_voice"][0]["persona_id"], "M04")
        self.assertEqual(len(ai_client.calls), 4)

    def test_runner_raises_when_planner_returns_invalid_json(self):
        module = self.load_or_fail()
        # Provide 3 invalid responses (matching PLANNER_RESPONSE_ATTEMPTS)
        ai_client = StubAIClient(
            responses=[
                {"mode": "live_text", "text": '{"task_breakdown": []}'},
                {"mode": "live_text", "text": '{"task_breakdown": []}'},
                {"mode": "live_text", "text": '{"task_breakdown": []}'},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        # After 3 retries, planner falls back with ready_to_dispatch=False,
        # which raises ResearchPlannerBlockedError
        with self.assertRaises((incomplete_error_type(module), planner_blocked_error_type(module))):
            runner.run(
                module.QualitativeResearchInput(
                    mode="multi",
                    question_type="copy_feedback",
                    user_question="这套文案会不会打动妈妈？",
                    copy_material="专业防蛀，孩子喜欢，妈妈省心。",
                )
            )

    def test_runner_raises_on_persona_mismatch(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M08")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        with self.assertRaises(incomplete_error_type(module)):
            runner.run(
                module.QualitativeResearchInput(
                    mode="single",
                    question_type="copy_feedback",
                    persona_id="M04",
                    user_question="高线忙碌妈妈会被哪句话打动？",
                    copy_material="专业防蛀，孩子喜欢，妈妈省心。",
                )
            )

    def test_runner_raises_when_synthesizer_output_is_invalid(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": '{"research_summary": {"consensus": []}}'},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        with self.assertRaises(incomplete_error_type(module)):
            runner.run(
                module.QualitativeResearchInput(
                    mode="single",
                    question_type="copy_feedback",
                    persona_id="M04",
                    user_question="高线忙碌妈妈会被哪句话打动？",
                    copy_material="专业防蛀，孩子喜欢，妈妈省心。",
                )
            )

    def test_report_contains_minimal_system_fingerprint(self):
        module = self.load_or_fail()
        module.collect_system_fingerprint = lambda base_dir, ai_client=None: {
            "git_sha": "test-sha",
            "env": "test",
            "model_id": "stub-model",
            "prompt_version": "qualitative-prompt-v1",
        }
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="高线忙碌妈妈会被哪句话打动？",
                copy_material="专业防蛀，孩子喜欢，妈妈省心。",
            )
        )

        fingerprint = report["meta"]["system_fingerprint"]
        self.assertEqual(fingerprint["git_sha"], "test-sha")
        self.assertEqual(fingerprint["env"], "test")
        self.assertEqual(fingerprint["model_id"], "stub-model")
        self.assertEqual(fingerprint["prompt_version"], "qualitative-prompt-v1")
        self.assertEqual(report["meta"]["schema_version"], "qualitative-report-v2")

    def test_packaging_review_prompt_contains_mode_focus(self):
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="packaging_review",
                persona_id="M04",
                user_question="这个包装是否清晰且可信？",
                product_info="儿童牙膏新包装，强调低氟防蛀。",
            )
        )

        planner_prompt = ai_client.calls[0]["prompt"]
        persona_prompt = ai_client.calls[1]["prompt"]
        synthesis_prompt = ai_client.calls[2]["prompt"]

        self.assertIn("包装评审", planner_prompt)
        self.assertIn("包装评审", persona_prompt)
        self.assertIn("shelf impact", synthesis_prompt)

    def test_ab_test_synthesis_requires_recommended_actions(self):
        module = self.load_or_fail()
        invalid_payload = {
            "research_summary": {
                "consensus": ["A更清晰"],
                "differences": ["B更有吸引力"],
                "pain_points": ["两版都缺证据"],
                "drivers": ["A信息完整"],
                "barriers": ["B可信度不足"],
                "copy_insights": ["开头要更直给"],
                "recommendations": ["继续迭代"],
            },
            "structured_recommendation": {
                "objective_answers": ["A整体更优"],
                "cross_persona_consensus": ["A更易理解"],
                "cross_persona_differences": ["价格敏感人群对B更宽容"],
                "key_risks": ["证据不够"],
                "opportunity_areas": ["补强信任素材"],
                "recommended_actions": [],
                "copy_or_product_adjustments": ["强化CTA"],
                "evidence_gaps": ["缺真实场景反馈"],
                "confidence_assessment": ["中等信心"],
            },
        }

        with self.assertRaises(incomplete_error_type(module)):
            module._validate_synthesis_payload(invalid_payload, "ab_test")

    def test_persona_rubric_scores_use_task_type_dimensions(self):
        """Verify concept_test persona prompt uses scoring_registry dimensions, not legacy."""
        module = self.load_or_fail()
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M04"],
                    ),
                },
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="concept_test",
                persona_id="M04",
                user_question="这个概念妈妈会不会买？",
                product_info="儿童牙膏，低氟防蛀。",
            )
        )

        persona_prompt = ai_client.calls[1]["prompt"]
        # concept_test dimensions should appear, NOT legacy ones
        self.assertIn("demand_fit", persona_prompt)
        self.assertIn("differentiation", persona_prompt)
        self.assertIn("purchase_drive", persona_prompt)
        self.assertIn("price_acceptance", persona_prompt)
        # Legacy dimension keys should NOT be in the rubric_scores format line
        self.assertNotIn("efficacy_clarity: 1-5", persona_prompt)
        self.assertNotIn("trust_signal: 1-5", persona_prompt)

    def test_planner_json_parse_failure_retries(self):
        """Verify planner retries when LLM returns markdown-wrapped JSON."""
        module = self.load_or_fail()
        # First response: markdown-wrapped JSON (should fail parse, then retry)
        # Second response: valid JSON
        ai_client = StubAIClient(
            responses=[
                {"mode": "live_text", "text": "```json\n" + planner_json(
                    ready_to_dispatch=True,
                    dispatch_scope="single",
                    target_personas=["M04"],
                ) + "\n```"},
                {"mode": "live_text", "text": mom_json("M04")},
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                persona_id="M04",
                user_question="这个文案好不好？",
                copy_material="专业防蛀。",
            )
        )
        # The markdown-fenced JSON should parse successfully via _parse_json_object
        # (it strips fences), so this should work in 3 calls total
        self.assertEqual(len(ai_client.calls), 3)
        self.assertEqual(report["meta"]["total_agents"], 1)

    def test_planner_fallback_does_not_dispatch(self):
        """Verify planner fallback sets ready_to_dispatch=False to block waste."""
        module = self.load_or_fail()
        # All 3 planner attempts return fallback_text → trigger fallback
        ai_client = StubAIClient(
            responses=[
                {"mode": "fallback_text", "text": "fail", "errors": ["timeout"]},
                {"mode": "fallback_text", "text": "fail", "errors": ["timeout"]},
                {"mode": "fallback_text", "text": "fail", "errors": ["timeout"]},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        plan = runner.plan(
            module.QualitativeResearchInput(
                mode="multi",
                question_type="purchase_decision",
                user_question="妈妈会不会买？",
                product_info="儿童牙膏",
            )
        )

        # Fallback plan should NOT dispatch (no live LLM available)
        self.assertFalse(plan["ready_to_dispatch"])
        # Should have clarifying questions about API config
        self.assertTrue(len(plan["clarifying_questions"]) > 0)
        self.assertEqual(len(ai_client.calls), 3)

    def test_persona_partial_failure_continues(self):
        """When one persona fails after retries, the error propagates."""
        module = self.load_or_fail()

        def mom_json_with_rubrics(persona_id: str) -> str:
            return json.dumps({
                "persona_id": persona_id,
                "persona_name": f"{persona_id}-mom",
                "task_responses": [{"question": "你会不会买", "answer": "会考虑"}],
                "dimension_scores": [{"dimension": "需求匹配度", "judgement": "还可以"}],
                "stance": "interested",
                "rubric_scores": {"demand_fit": 4, "differentiation": 3, "purchase_drive": 4, "price_acceptance": 3},
                "triggered_veto_codes": [],
                "core_needs": ["安全"],
                "motivations": ["有效果"],
                "concerns": [],
                "decision_logic": "看需求匹配就买。",
                "verbatim_answer": "会试试。",
                "evidence_trace": "需求匹配好。",
            }, ensure_ascii=False)

        # Single persona that first returns fallback, then succeeds on retry
        ai_client = StubAIClient(
            responses=[
                {
                    "mode": "live_text",
                    "text": planner_json(
                        ready_to_dispatch=True,
                        dispatch_scope="single",
                        target_personas=["M01"],
                    ),
                },
                # M01: 2 fallback attempts, then succeeds
                {"mode": "fallback_text", "text": "fail", "errors": ["timeout"]},
                {"mode": "fallback_text", "text": "fail", "errors": ["timeout"]},
                {"mode": "live_text", "text": mom_json_with_rubrics("M01")},
                # Synthesizer
                {"mode": "live_text", "text": synthesis_json()},
            ]
        )
        runner = module.QualitativeResearchRunner(self.persona_path, ai_client=ai_client)

        report = runner.run(
            module.QualitativeResearchInput(
                mode="single",
                question_type="concept_test",
                persona_id="M01",
                user_question="这个概念怎么样？",
                product_info="儿童牙膏",
            )
        )

        self.assertEqual(report["meta"]["agent_count_completed"], 1)
        self.assertEqual(report["meta"]["completion_status"], "complete")
        self.assertEqual(len(ai_client.calls), 5)  # 1 planner + 3 persona (2 retry + 1 success) + 1 synth


if __name__ == "__main__":
    unittest.main()
