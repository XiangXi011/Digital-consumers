import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dingtalk_stream_service import DingTalkLangGraphHandler, DingTalkStreamConfig
from html_report_renderer import HTMLReportRenderer
from privacy_utils import sanitize_report
from business_brief import BusinessBrief
from qualitative_research import QualitativeResearchInput, ResearchSynthesizerAgent
from redis_infra import InMemoryStore
from task_session_manager import TaskSession, TaskSessionManager
from langgraph_nodes import make_build_research_input_node, make_readiness_gate_node


def _persona_path() -> Path:
    return Path(__file__).resolve().parents[1] / "persona_samples_complete.json"


class RecordingAIClient:
    is_configured = True

    def __init__(self, text: str):
        self.text = text
        self.calls = []

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return {"mode": "live_text", "text": self.text}


class FakeWorkflow:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.research_input_cls = QualitativeResearchInput


class GuardedWorkflow:
    def __init__(self):
        self.calls = []
        self.session_manager = type(
            "SessionManager",
            (),
            {"find_session_for": staticmethod(lambda group_id, conversation_id, user_id: None)},
        )()

    def handle_message(self, event):
        self.calls.append(event)
        return {"status": "collecting", "messages": [], "task_id": None}


class FinalLockContractTest(unittest.TestCase):
    def test_purchase_decision_question_type_survives_business_brief_projection(self):
        session = TaskSession(
            session_id="s-purchase",
            group_id="g1",
            conversation_id="c1",
            user_id="u1",
        )
        session.fields["question_type"]["status"] = "provided"
        session.fields["question_type"]["value"] = "purchase_decision"
        session.fields["user_question"]["status"] = "provided"
        session.fields["user_question"]["value"] = "Will moms actually buy this?"
        session.fields["product_info"]["status"] = "provided"
        session.fields["product_info"]["value"] = "Kids toothpaste"

        brief = BusinessBrief.from_session_fields(session.fields)
        payload = brief.to_research_input_payload(mode="multi")

        self.assertEqual(brief.task_type, "concept_test")
        self.assertEqual(brief.question_type, "purchase_decision")
        self.assertEqual(payload["question_type"], "purchase_decision")

    def test_multi_eight_mom_request_defaults_to_builtin_persona_pack(self):
        session = TaskSession(
            session_id="s-eight-moms",
            group_id="g1",
            conversation_id="c1",
            user_id="u1",
        )
        session.fields["mode"]["status"] = "provided"
        session.fields["mode"]["value"] = "multi"
        session.fields["question_type"]["status"] = "provided"
        session.fields["question_type"]["value"] = "purchase_decision"
        session.fields["user_question"]["status"] = "provided"
        session.fields["user_question"]["value"] = "8类妈妈会不会买这款儿童牙膏？"
        session.fields["product_info"]["status"] = "provided"
        session.fields["product_info"]["value"] = "低氟防蛀儿童牙膏"

        brief = BusinessBrief.from_session_fields(session.fields)
        payload = brief.to_research_input_payload(mode="multi")

        self.assertEqual(brief.persona_pack_id, "default-eight-moms-v1")
        self.assertEqual(len(brief.audience_segments or []), 8)
        self.assertIn("M01 宠爱富养家", brief.audience_segments)
        self.assertEqual(payload["persona_pack_id"], "default-eight-moms-v1")
        self.assertEqual(len(payload["audience_segments"]), 8)

    def test_price_and_ab_inputs_are_reachable_from_normal_intake_fields(self):
        price_session = TaskSession(
            session_id="s-price",
            group_id="g1",
            conversation_id="c1",
            user_id="u1",
        )
        price_session.fields["question_type"]["status"] = "provided"
        price_session.fields["question_type"]["value"] = "price_test"
        price_session.fields["user_question"]["status"] = "provided"
        price_session.fields["user_question"]["value"] = "Is 39 RMB acceptable?"
        price_session.fields["product_info"]["status"] = "provided"
        price_session.fields["product_info"]["value"] = "Kids toothpaste"
        price_session.fields["price_test_mode"]["status"] = "provided"
        price_session.fields["price_test_mode"]["value"] = "relative_price"
        price_session.fields["price_range"]["status"] = "provided"
        price_session.fields["price_range"]["value"] = "29-39"
        price_session.fields["benchmark_reference"]["status"] = "provided"
        price_session.fields["benchmark_reference"]["value"] = "Crest kids toothpaste"

        ab_session = TaskSession(
            session_id="s-ab",
            group_id="g1",
            conversation_id="c1",
            user_id="u1",
        )
        ab_session.fields["question_type"]["status"] = "provided"
        ab_session.fields["question_type"]["value"] = "ab_test"
        ab_session.fields["user_question"]["status"] = "provided"
        ab_session.fields["user_question"]["value"] = "Which headline wins?"
        ab_session.fields["product_info"]["status"] = "provided"
        ab_session.fields["product_info"]["value"] = "Kids toothpaste"
        ab_session.fields["copy_material"]["status"] = "provided"
        ab_session.fields["copy_material"]["value"] = "A版：医生推荐\nB版：孩子爱刷牙"

        price_brief = BusinessBrief.from_session_fields(price_session.fields)
        ab_brief = BusinessBrief.from_session_fields(ab_session.fields)

        self.assertEqual(price_brief.task_type, "price_test")
        self.assertEqual(price_brief.question_type, "price_test")
        self.assertEqual(price_brief.price_test_mode, "relative_price")
        self.assertEqual(price_brief.price_range, "29-39")
        self.assertEqual(price_brief.benchmark_reference, ["Crest kids toothpaste"])
        self.assertEqual(ab_brief.task_type, "ab_test")
        self.assertEqual(ab_brief.question_type, "ab_test")
        self.assertEqual(ab_brief.copy_candidates, ["A版：医生推荐", "B版：孩子爱刷牙"])

    def test_business_brief_combines_typed_product_text_ocr_notes_and_source_links(self):
        session = TaskSession(
            session_id="s-product-context",
            group_id="g1",
            conversation_id="c1",
            user_id="u1",
        )
        session.fields["question_type"]["status"] = "provided"
        session.fields["question_type"]["value"] = "copy_feedback"
        session.fields["user_question"]["status"] = "provided"
        session.fields["user_question"]["value"] = "妈妈会不会买这款洗发水？"
        session.fields["product_info"]["status"] = "provided"
        session.fields["product_info"]["value"] = "成人洗发水"
        session.fields["background_material"]["status"] = "provided"
        session.fields["background_material"]["value"] = "头皮清爽，48小时控油。"

        brief = BusinessBrief.from_session_fields(
            session.fields,
            source_links=["https://detail.tmall.com/item.htm?id=67890"],
            custom_questions=["会不会太贵？"],
            product_context_notes=[
                "brand: Saky Kids",
                "category: 儿童牙膏",
                "packaging_summary: 蓝白包装的儿童牙膏详情页。",
            ],
        )

        self.assertEqual(
            brief.product_context,
            "\n".join(
                [
                    "成人洗发水",
                    "头皮清爽，48小时控油。",
                    "brand: Saky Kids",
                    "category: 儿童牙膏",
                    "packaging_summary: 蓝白包装的儿童牙膏详情页。",
                    "source_links: https://detail.tmall.com/item.htm?id=67890",
                ]
            ),
        )
        self.assertEqual(brief.source_links, ["https://detail.tmall.com/item.htm?id=67890"])
        self.assertEqual(brief.custom_questions, ["会不会太贵？"])

    def test_business_brief_combines_product_text_and_ocr_notes(self):
        """Test that product_info + background + OCR notes are combined without source_links."""
        session = TaskSession(
            session_id="s-product-context-2",
            group_id="g1",
            conversation_id="c1",
            user_id="u1",
        )
        session.fields["question_type"]["status"] = "provided"
        session.fields["question_type"]["value"] = "copy_feedback"
        session.fields["user_question"]["status"] = "provided"
        session.fields["user_question"]["value"] = "文案是否吸引妈妈？"
        session.fields["product_info"]["status"] = "provided"
        session.fields["product_info"]["value"] = "儿童面霜"
        session.fields["background_material"]["status"] = "provided"
        session.fields["background_material"]["value"] = "天然成分，无添加。"

        brief = BusinessBrief.from_session_fields(
            session.fields,
            source_links=[],
            custom_questions=["有没有副作用？"],
            product_context_notes=[
                "brand: MamaBear",
                "category: 儿童护肤",
            ],
        )

        # No source_links line when empty
        self.assertEqual(
            brief.product_context,
            "\n".join(
                [
                    "儿童面霜",
                    "天然成分，无添加。",
                    "brand: MamaBear",
                    "category: 儿童护肤",
                ]
            ),
        )
        self.assertEqual(brief.source_links, [])
        self.assertEqual(brief.custom_questions, ["有没有副作用？"])

    def test_session_storage_is_desensitized_and_retention_tagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "sessions"
            manager = TaskSessionManager(
                session_dir=session_dir,
                persona_path=_persona_path(),
            )
            session = manager.get_or_create(
                group_id="raw-group-id",
                conversation_id="raw-conversation-id",
                user_id="raw-user-id",
            )
            session.authorization_requested_by = "raw-user-id"
            manager.save(session)

            payload = json.loads(next(session_dir.glob("*.json")).read_text(encoding="utf-8"))

        self.assertTrue(payload["identifiers_hashed"])
        self.assertNotEqual(payload["group_id"], "raw-group-id")
        self.assertNotEqual(payload["conversation_id"], "raw-conversation-id")
        self.assertNotEqual(payload["user_id"], "raw-user-id")
        self.assertNotEqual(payload["authorization_requested_by"], "raw-user-id")
        self.assertEqual(payload["retention_policy"]["raw_text_days"], 30)
        self.assertEqual(payload["retention_policy"]["debug_json_days"], 90)

    def test_invalid_status_jump_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskSessionManager(
                session_dir=Path(tmp) / "sessions",
                persona_path=_persona_path(),
            )
            session = manager.get_or_create("group-1", "conv-1", "user-1")
            session.status = "completed"

            with self.assertRaises(ValueError):
                manager.save(session)

    def test_sanitize_report_redacts_generic_session_identifiers(self):
        html = "<div>session_id: group-1:conv-1:user-1</div><div>trace_id: abc123</div>"

        sanitized = sanitize_report(html)

        self.assertNotIn("group-1:conv-1:user-1", sanitized)
        self.assertNotIn("abc123", sanitized)

    def test_downstream_uses_business_brief_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = TaskSessionManager(
                session_dir=Path(tmp) / "sessions",
                persona_path=_persona_path(),
            )
            workflow = FakeWorkflow(manager)
            session = TaskSession(
                session_id="s1",
                group_id="g1",
                conversation_id="c1",
                user_id="u1",
            )
            session.fields["question_type"]["status"] = "provided"
            session.fields["question_type"]["value"] = "copy_feedback"
            session.fields["user_question"]["status"] = "provided"
            session.fields["user_question"]["value"] = "OLD QUESTION"
            session.fields["product_info"]["status"] = "provided"
            session.fields["product_info"]["value"] = "OLD PRODUCT"

            node = make_build_research_input_node(workflow)
            result = node(
                {
                    "session": session,
                    "research_plan": {"dispatch_scope": "single"},
                    "business_brief": {
                        "task_type": "price_test",
                        "research_goal": "NEW GOAL",
                        "product_context": "NEW PRODUCT",
                        "price_test_mode": "absolute_price",
                        "price_range": "29-39",
                        "key_claims": ["proof", "taste"],
                    },
                }
            )

            self.assertEqual(result["research_input"].user_question, "NEW GOAL")
            self.assertEqual(result["research_input"].product_info, "NEW PRODUCT")
            self.assertEqual(result["research_input"].question_type, "price_test")

    def test_readiness_gate_is_single_decider(self):
        node = make_readiness_gate_node(object())
        blocked = node(
            {
                "authorization_result": "strong_affirm",
                "business_brief": {
                    "task_type": "copy_feedback",
                    "product_context": "",
                    "research_goal": "Need copy feedback",
                },
            }
        )
        ready = node(
            {
                "authorization_result": "strong_affirm",
                "business_brief": {
                    "task_type": "copy_feedback",
                    "product_context": "Kids toothpaste",
                    "research_goal": "Need copy feedback",
                    "key_claims": ["Low fluoride", "Better taste"],
                },
            }
        )

        self.assertEqual(blocked["recommended_state"], "awaiting_clarification")
        self.assertIn("product_context", blocked["blocking_reasons"])
        self.assertEqual(ready["recommended_state"], "ready_to_dispatch")
        self.assertEqual(ready["blocking_reasons"], [])

    def test_ra_prompt_excludes_raw_persona_outputs(self):
        ai_client = RecordingAIClient(
            json.dumps(
                {
                    "research_summary": {
                        "consensus": ["Need stronger proof"],
                        "differences": ["Price sensitivity varies"],
                        "pain_points": ["Trust gap"],
                        "drivers": ["Clinical proof"],
                        "barriers": ["Weak evidence"],
                        "copy_insights": ["Lead with proof"],
                        "recommendations": ["Tighten claims"],
                    },
                    "structured_recommendation": {
                        "objective_answers": ["Consumers need proof"],
                        "cross_persona_consensus": ["Trust dominates"],
                        "cross_persona_differences": ["Price varies by persona"],
                        "key_risks": ["Evidence is thin"],
                        "opportunity_areas": ["Sharper proof assets"],
                        "recommended_actions": ["Rewrite hero message"],
                        "copy_or_product_adjustments": ["Add concrete proof points"],
                        "evidence_gaps": ["Missing user trial data"],
                        "confidence_assessment": ["Directionally strong"],
                    },
                },
                ensure_ascii=False,
            )
        )
        agent = ResearchSynthesizerAgent(ai_client)
        mom_outputs = [
            {
                "persona_id": "M01",
                "persona_name": "M01-mom",
                "stance": "rejecting",
                "core_needs": ["Trust"],
                "motivations": [],
                "concerns": ["Need stronger proof"],
                "rubric_scores": {
                    "efficacy_clarity": 2,
                    "trust_signal": 2,
                    "convenience": 3,
                    "price_fit": 3,
                },
                "verbatim_answer": "I would not buy this yet.",
            }
        ]

        agent.run(
            QualitativeResearchInput(
                mode="single",
                question_type="copy_feedback",
                user_question="Will this work?",
                product_info="Kids toothpaste",
            ),
            {"dispatch_scope": "single", "target_personas": ["M01"]},
            mom_outputs,
        )

        prompt = ai_client.calls[0]["prompt"]
        self.assertIn("minority_reject_evidence", prompt)
        self.assertNotIn("=== 鍘熷濡堝鐢诲儚杈撳嚭", prompt)
        self.assertNotIn("I would not buy this yet.", prompt)

    def test_runtime_guards_are_applied_at_ingress(self):
        workflow = GuardedWorkflow()
        handler = DingTalkLangGraphHandler(
            workflow,
            DingTalkStreamConfig(app_key="k", app_secret="s"),
            runtime_store=InMemoryStore(),
        )

        event = {
            "group_id": "group-1",
            "conversation_id": "conv-1",
            "user_id": "user-1",
            "text": "hello",
            "attachments": [],
            "create_ts": 1000,
            "msg_id": "msg-1",
            "event_type": "message",
        }

        self.assertTrue(handler._apply_runtime_guards(dict(event)))
        self.assertFalse(handler._apply_runtime_guards(dict(event)))
        self.assertFalse(handler._apply_runtime_guards({**event, "msg_id": "msg-2", "create_ts": 999}))
        self.assertTrue(handler._apply_runtime_guards({**event, "msg_id": "msg-3", "create_ts": 1001}))

    def test_html_and_privacy_contract(self):
        renderer = HTMLReportRenderer()
        report = {
            "meta": {
                "mode": "multi",
                "question_type": "copy_feedback",
                "generated_at": "2026-03-16 10:00:00",
                "total_agents": 8,
            },
            "research_brief": {
                "user_question": "Will moms buy this?",
                "product_info": "Kids toothpaste with clinical proof",
                "copy_material": "Low fluoride\nBetter taste",
                "background_material": "Background note",
                "assumptions": ["Assume broad audience"],
                "risk_flags": ["Channel unspecified"],
            },
            "research_summary": {
                "consensus": ["Trust matters most"],
                "differences": ["Price sensitivity varies"],
                "pain_points": ["Weak proof"],
                "drivers": ["Clinical validation"],
                "barriers": ["Low trust"],
            },
            "structured_recommendation": {
                "objective_answers": ["Need stronger proof"],
                "recommended_actions": ["Rewrite hero message"],
                "copy_or_product_adjustments": ["Add evidence"],
                "evidence_gaps": ["Missing usage study"],
                "confidence_assessment": ["Directionally strong"],
            },
            "consumer_voice": [
                {
                    "persona_id": "M01",
                    "persona_name": "M01-mom",
                    "voice_line": "I need stronger proof first.",
                    "what_would_change_my_mind": "Show clinical proof.",
                    "backend_evaluation": {
                        "purchase_intent": "reject",
                        "purchase_score": 2.7,
                    },
                    "rubric_scores": {
                        "efficacy_clarity": 2,
                        "trust_signal": 2,
                        "convenience": 3,
                        "price_fit": 4,
                    },
                    "concerns": ["Weak proof"],
                    "motivations": ["Safer ingredients"],
                }
            ],
            "appendix": {
                "follow_up_context": "User asked for copy feedback",
                "attachments": ["trace_id=abc123 raw_chat=secret"],
            },
        }

        html = renderer.render(report)
        sanitized = sanitize_report(html)

        self.assertIn("cover information", html)
        self.assertIn("downgrade and assumptions", html)
        self.assertIn("one-line conclusion", html)
        self.assertIn("eight persona cards", html)
        self.assertIn("purchase_intent", html)
        self.assertIn("purchase_score", html)
        self.assertIn("what_would_change_my_mind", html)
        self.assertNotIn("trace_id", sanitized)
        self.assertNotIn("raw_chat", sanitized)


if __name__ == "__main__":
    unittest.main()
