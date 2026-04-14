import json
from typing import Any, Dict

import logging

from backend.infra.prompt_shield import check_prompt_injection, get_prompt_injection_label

logger = logging.getLogger(__name__)


def make_load_session_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        event = state["event"]
        session = workflow.session_manager.get_or_create(
            group_id=event["group_id"],
            conversation_id=event["conversation_id"],
            user_id=event["user_id"],
        )
        return {"session": session, "status": session.status}

    return node


def make_detect_command_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        text = state["event"].get("text", "").strip()
        return {"reset_requested": workflow.session_manager.has_reset_command(text)}

    return node


def make_prompt_shield_node(workflow):
    """Pre-routing prompt injection shield (runtime-and-state.md §Pre-Routing Shield).

    Must run before any LLM call. If injection detected, the message
    is rejected and a warning is returned to the user.
    """
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        text = state["event"].get("text", "").strip()
        is_injection = check_prompt_injection(text)
        if is_injection:
            label = get_prompt_injection_label(text)
            logger.warning("Prompt shield blocked message. label=%s text_preview=%r", label, text[:240])
            session = state["session"]
            response = workflow._response(
                session,
                [{"type": "text", "content": f"检测到不安全的指令内容（命中: {label or 'unknown'}），该消息已被拦截。请发送正常的研究任务信息。"}],
            )
            return {
                "prompt_injection_detected": True,
                "response": response,
            }
        return {"prompt_injection_detected": False}

    return node


def route_after_prompt_shield(state: Dict[str, Any]) -> str:
    """Route after prompt shield: if injection detected, go to end; otherwise continue."""
    if state.get("prompt_injection_detected"):
        return "end"
    return "continue"


def route_after_detect_command(state: Dict[str, Any]) -> str:
    if state.get("reset_requested"):
        return "reset_session"
    # First message should be ingested first (checklist becomes follow-up aid, not hard gate)
    return "ingest_message"


def make_reset_session_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        event = state["event"]
        session = workflow.session_manager.reset_session(
            group_id=event["group_id"],
            conversation_id=event["conversation_id"],
            user_id=event["user_id"],
        )
        return {"session": session, "status": session.status, "reset_completed": True}

    return node


def make_send_checklist_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        session.checklist_sent = True
        session.status = "collecting"
        workflow.session_manager.save(session)
        content = workflow.session_manager.checklist_text()
        if state.get("reset_completed"):
            content = f"{workflow.session_manager.reset_confirmation_text()}\n\n{content}"
        response = workflow._response(session, [{"type": "text", "content": content}])
        return {"session": session, "status": session.status, "response": response}

    return node


def make_ingest_message_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        event = state["event"]
        text = event.get("text", "").strip()
        attachments = event.get("attachments", [])
        followup_relation = ""
        prior_brief_snapshot_ref = ""

        if session.status == "completed" and session.business_brief and text:
            from backend.domain.business_brief import BusinessBrief
            from backend.workflow.followup_adjudicator import adjudicate_followup, check_same_task_preconditions

            prior_brief = dict(session.business_brief or {})
            prior_brief_text = json.dumps(prior_brief, ensure_ascii=False)
            prior_brief_snapshot_ref = session.frozen_snapshot_refs[-1] if session.frozen_snapshot_refs else ""

            # Build candidate Brief BEFORE follow-up adjudication (BusinessBrief boundary)
            candidate_fields = workflow.session_manager.preview_fields_from_text(text)
            candidate_brief = BusinessBrief.from_session_fields(candidate_fields).model_dump()
            candidate_brief_text = json.dumps(candidate_brief, ensure_ascii=False)

            followup_decision = adjudicate_followup(candidate_brief_text, prior_brief_text)

            if followup_decision == "unrelated":
                followup_relation = "unrelated"
                session = workflow.session_manager.start_new_task(session)
            else:
                if check_same_task_preconditions(prior_brief, candidate_brief):
                    followup_relation = "same_task"
                else:
                    followup_relation = "same_topic_new_task"
                    session = workflow.session_manager.start_new_task(session)

        # Update session and use the returned object directly to avoid
        # potential race conditions with concurrent modifications
        session = workflow.session_manager.update_from_message(session, text, attachments=attachments)
        explicit_run_requested = workflow.session_manager.has_run_confirmation(text)
        authorization_result = workflow.session_manager.classify_authorization(
            text, event.get("user_id", ""), event, session=session,
        )
        missing_fields = list(session.missing_fields)

        return {
            "session": session,
            "explicit_run_requested": explicit_run_requested,
            "authorization_result": authorization_result,
            "missing_fields": missing_fields,
            "followup_relation": followup_relation,
            "prior_brief_snapshot_ref": prior_brief_snapshot_ref,
        }

    return node


def make_readiness_gate_node(workflow):
    """ReadinessGate — the ONLY node that decides whether info is sufficient.

    Per master-spec.md: ReadinessGate is the only node allowed to decide
    whether information is sufficient for execution. Centralizes readiness
    logic that was previously split between ingest_message and start_analysis.
    """
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        from backend.domain.business_brief import BusinessBrief

        authorization_result = state.get("authorization_result", "none")
        authorized = authorization_result in ("strong_affirm", "weak_affirm")
        brief_payload = state.get("business_brief") or {}
        if not brief_payload and state.get("session") is not None:
            brief_payload = BusinessBrief.from_session_fields(
                state["session"].fields,
                source_links=list(getattr(state["session"], "source_links", [])),
                custom_questions=list(getattr(state["session"], "custom_questions", [])),
                product_context_notes=list(getattr(state["session"], "product_context_notes", [])),
                followup_relation=state.get("followup_relation") or None,
                prior_brief_snapshot_ref=state.get("prior_brief_snapshot_ref") or None,
            ).model_dump()

        brief = BusinessBrief.model_validate(brief_payload)
        blocking_reasons = []
        product_context_lines = [
            line.strip()
            for line in brief.product_context.splitlines()
            if line.strip()
        ]
        has_substantive_product_context = any(
            not line.lower().startswith("source_links:")
            for line in product_context_lines
        )

        if not authorized:
            blocking_reasons.append("authorization_required")
        if not brief.research_goal.strip():
            blocking_reasons.append("research_goal")
        if not has_substantive_product_context:
            blocking_reasons.append("product_context")
        session = state.get("session")
        if session is not None and session.fields["mode"]["value"] == "single":
            if not session.fields["persona_id"]["value"]:
                blocking_reasons.append("persona_id")
        if brief.task_type in {"copy_feedback", "ab_test"} and not (
            brief.copy_candidates or brief.key_claims or (brief.task_type == "ab_test" and has_substantive_product_context)
        ):
            blocking_reasons.append("copy_candidates")
        if brief.task_type == "price_test":
            if not brief.price_test_mode:
                blocking_reasons.append("price_test_mode")
            if not brief.price_range:
                blocking_reasons.append("price_range")
            if brief.price_test_mode == "relative_price" and not brief.benchmark_reference:
                blocking_reasons.append("benchmark_reference")

        recommended_state = "ready_to_dispatch"
        if blocking_reasons:
            has_auth = "authorization_required" in blocking_reasons
            has_other = any(r != "authorization_required" for r in blocking_reasons)
            if has_auth and has_other:
                # Both auth and info missing: auth takes priority
                recommended_state = "awaiting_authorization"
            elif has_auth:
                recommended_state = "awaiting_authorization"
            else:
                recommended_state = "awaiting_clarification"

        readiness_passed = recommended_state == "ready_to_dispatch"
        readiness_decision = {
            "recommended_state": recommended_state,
            "blocking_reasons": blocking_reasons,
            "authorization_needed": not authorized,
        }
        if session is not None and hasattr(workflow, "session_manager"):
            session.readiness_decision = readiness_decision
            workflow.session_manager.save_live_snapshot(
                session,
                "readiness",
                {
                    "business_brief": brief.model_dump(),
                    "readiness_decision": readiness_decision,
                },
            )
        return {
            "readiness_passed": readiness_passed,
            "readiness_decision": readiness_decision,
            "recommended_state": recommended_state,
            "blocking_reasons": blocking_reasons,
            "authorization_needed": not authorized,
            "business_brief": brief.model_dump(),
        }

    return node


def route_after_readiness_gate(state: Dict[str, Any]) -> str:
    """Route after ReadinessGate check."""
    decision = state.get("readiness_decision", {})
    if decision.get("recommended_state") == "ready_to_dispatch":
        return "build_business_brief"
    return "send_follow_up"


def make_build_business_brief_node(workflow):
    """Convert session fields into a typed BusinessBrief.

    Per master-spec.md: downstream nodes must consume BusinessBrief,
    not raw chat or untyped session fields.
    """
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        from backend.domain.business_brief import BusinessBrief

        session = state["session"]
        brief = BusinessBrief.from_session_fields(
            session.fields,
            source_links=list(getattr(session, "source_links", [])),
            custom_questions=list(getattr(session, "custom_questions", [])),
            product_context_notes=list(getattr(session, "product_context_notes", [])),
            followup_relation=state.get("followup_relation") or None,
            prior_brief_snapshot_ref=state.get("prior_brief_snapshot_ref") or None,
        )
        session.business_brief = brief.model_dump()
        workflow.session_manager.save(session)
        return {"session": session, "business_brief": brief.model_dump()}

    return node


def make_send_follow_up_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        import time

        session = state["session"]
        event = state.get("event", {})
        readiness = state.get("readiness_decision", {})
        session.readiness_decision = readiness or session.readiness_decision
        recommended_state = readiness.get("recommended_state")
        if recommended_state == "awaiting_authorization":
            session.status = "awaiting_run_confirmation"
        elif recommended_state == "awaiting_clarification":
            session.status = "awaiting_clarification"
        else:
            session.status = "collecting"
        if session.status == "awaiting_clarification" and not session.checklist_sent:
            session.checklist_sent = True
            session.status = "collecting"
            workflow.session_manager.save(session)
            content = workflow.session_manager.checklist_text()
            response = workflow._response(
                session,
                [{"type": "text", "content": content}],
            )
            return {"session": session, "status": session.status, "response": response}
        if session.status == "awaiting_run_confirmation":
            session.authorization_requested_at = event.get("create_ts") or time.time() * 1000
            session.authorization_requested_by = event.get("user_id", session.user_id)
            workflow.session_manager.save_live_snapshot(
                session,
                "authorization",
                {
                    "authorization_requested_at": session.authorization_requested_at,
                    "authorization_requested_by": session.authorization_requested_by,
                    "readiness_decision": readiness,
                },
            )
        workflow.session_manager.save(session)
        if session.status == "awaiting_clarification":
            content = workflow.session_manager.build_readiness_clarification_text(readiness)
        else:
            content = workflow.session_manager.build_follow_up_text(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": content}],
        )
        return {"session": session, "status": session.status, "response": response}

    return node


def make_start_analysis_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        brief_payload = state.get("business_brief") or session.business_brief
        research_input = workflow.research_input_cls(
            **workflow.session_manager.build_research_input_payload(
                session,
                business_brief=brief_payload,
            )
        )

        session.status = "planning"
        session.business_brief = brief_payload
        workflow.session_manager.save(session)

        research_plan = workflow.runner.plan(research_input)
        session.research_plan = research_plan

        session.partial_run_authorized = bool(state.get("explicit_run_requested"))
        session.status = "running"
        session.last_task_id = f"{session.session_id}__run"
        workflow.session_manager.save_frozen_snapshot(
            session,
            "dispatch",
            {
                "business_brief": brief_payload,
                "research_input": state.get("research_input_payload")
                or workflow.session_manager.build_research_input_payload(
                    session,
                    business_brief=brief_payload,
                ),
                "research_plan": research_plan,
            },
        )
        workflow.session_manager.save(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": "开始生成妈妈原声与研究总结"}],
            task_id=session.last_task_id,
        )
        return {
            "session": session,
            "status": session.status,
            "task_id": session.last_task_id,
            "research_plan": research_plan,
            "response": response,
        }

    return node


def make_workflow_error_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state.get("session")
        if session is None:
            event = state.get("event", {})
            session = workflow.session_manager.get_or_create(
                group_id=event.get("group_id", "unknown-group"),
                conversation_id=event.get("conversation_id", "unknown-conversation"),
                user_id=event.get("user_id", "unknown-user"),
            )
        session.status = "error"
        workflow.session_manager.save(session)
        response = workflow._response(session, [{"type": "text", "content": "处理研究任务时发生错误，请稍后再试。"}])
        return {"session": session, "status": session.status, "response": response}

    return node


def make_load_task_session_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        task_id = state["task_id"]
        session_id = task_id.rsplit("__run", 1)[0]
        session = workflow.session_manager.load(session_id)
        return {"session": session, "research_plan": session.research_plan}

    return node


def make_build_research_input_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        payload = workflow.session_manager.build_research_input_payload(
            state["session"],
            business_brief=state.get("business_brief"),
        )
        research_input = workflow.research_input_cls(**payload)
        return {
            "research_input_payload": payload,
            "research_input": research_input,
            "research_plan": state.get("research_plan") or state["session"].research_plan,
        }

    return node


def make_run_research_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        workflow.session_manager.save_frozen_snapshot(
            session,
            "synthesis",
            {
                "business_brief": state.get("business_brief") or session.business_brief,
                "research_input": state.get("research_input_payload")
                or workflow.session_manager.build_research_input_payload(
                    session,
                    business_brief=state.get("business_brief") or session.business_brief,
                ),
                "research_plan": state.get("research_plan") or session.research_plan,
            },
        )
        report = workflow.runner.run(
            state["research_input"],
            research_plan=state.get("research_plan"),
        )
        result = {"report": report}
        # Phase 3: extract group discussion and deep dive results into state
        if report.get("group_discussion"):
            result["group_discussion"] = report["group_discussion"]
        if report.get("deep_dive_results"):
            result["deep_dive_results"] = report["deep_dive_results"]
        return result

    return node


def make_render_html_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        html = workflow.renderer.render(state["report"])
        return {"html": html}

    return node


def make_persist_outputs_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        from backend.infra.privacy_utils import sanitize_report
        from backend.research.observability import compute_evaluation_metrics

        session = state["session"]
        task_id = session.last_task_id or state["task_id"]
        json_path = workflow.output_dir / f"{task_id}.json"
        html_path = workflow.output_dir / f"{task_id}.html"
        html = sanitize_report(state["html"])
        metrics = state["report"].get("meta", {}).get("evaluation_metrics")
        if not isinstance(metrics, dict) or not metrics:
            metrics = compute_evaluation_metrics(state["report"])
            state["report"].setdefault("meta", {})["evaluation_metrics"] = metrics

        json_path.write_text(json.dumps(state["report"], ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")
        session.metrics_path = workflow.session_manager.save_metrics_artifact(task_id, metrics)
        workflow.session_manager.save_frozen_snapshot(
            session,
            "reporting",
            {
                "report_meta": state["report"].get("meta", {}),
                "research_summary": state["report"].get("research_summary", {}),
                "structured_recommendation": state["report"].get("structured_recommendation", {}),
            },
        )

        session.status = "completed"
        session.html_report_path = str(html_path)
        session.json_report_path = str(json_path)
        session.follow_up_context = workflow._build_short_summary(state["report"])
        workflow.session_manager.save(session)
        return {
            "session": session,
            "status": session.status,
            "html_report_path": str(html_path),
            "json_report_path": str(json_path),
        }

    return node


def make_publish_report_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        publisher = getattr(workflow, "report_publisher", None)
        if not publisher:
            return {"public_report_url": ""}
        publish_result = publisher.publish_report(state["html_report_path"])
        return {"public_report_url": publish_result.get("public_report_url", "")}

    return node


def make_finalize_task_response_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        summary = workflow._build_short_summary(state["report"])
        response = workflow._response(
            session,
            [{"type": "text", "content": summary}],
            html_report_path=session.html_report_path,
            json_report_path=session.json_report_path,
            public_report_url=state.get("public_report_url", ""),
        )
        return {"response": response}

    return node
