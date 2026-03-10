import json
from pathlib import Path
from typing import Any, Dict


def make_build_product_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        concept_input = state["concept_input"]
        return {"product": concept_input.to_product()}

    return node


def make_evaluate_batch_node(runner):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        evaluation_results = runner.run_batch_evaluation(state["product"])
        return {"evaluation_results": evaluation_results}

    return node


def make_prepare_discussion_node(runner):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        evaluation_results = state["evaluation_results"]
        return {
            "discussion_participants": runner.select_discussion_participants(evaluation_results),
            "deep_dive_candidates": runner.select_deep_dive_candidates(evaluation_results),
        }

    return node


def make_run_discussion_node(runner):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        concept_input = state["concept_input"]
        discussion = runner.orchestrator.group_discussion(
            topic=runner._build_discussion_topic(concept_input),
            product=state["product"],
            participant_ids=state["discussion_participants"],
        )
        return {"discussion": discussion}

    return node


def make_run_deep_dives_node(runner):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        concept_input = state["concept_input"]
        questions = runner._build_deep_dive_questions(concept_input)
        deep_dives = {
            bucket: [
                runner.orchestrator.deep_dive(agent_id, questions)
                for agent_id in agent_ids
            ]
            for bucket, agent_ids in state["deep_dive_candidates"].items()
        }
        return {"deep_dives": deep_dives}

    return node


def make_build_report_node(runner):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator_report = runner.orchestrator.generate_report(state["evaluation_results"])
        report = runner._build_report(
            concept_input=state["concept_input"],
            product=state["product"],
            evaluation_results=state["evaluation_results"],
            orchestrator_report=orchestrator_report,
            discussion=state["discussion"],
            deep_dives=state["deep_dives"],
        )
        return {
            "orchestrator_report": orchestrator_report,
            "report": report,
            "markdown": runner.render_markdown_report(report),
        }

    return node


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


def make_ingest_message_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        event = state["event"]
        text = event.get("text", "").strip()
        attachments = event.get("attachments", [])

        workflow.session_manager.update_from_message(session, text, attachments=attachments)
        session = workflow.session_manager.load(session.session_id)
        explicit_run_requested = workflow.session_manager.has_run_confirmation(text)
        has_minimum = workflow.session_manager.has_minimum_runnable_info(session)
        missing_fields = list(session.missing_fields)

        return {
            "session": session,
            "explicit_run_requested": explicit_run_requested,
            "has_minimum_runnable_info": has_minimum,
            "missing_fields": missing_fields,
        }

    return node


def route_after_detect_command(state: Dict[str, Any]) -> str:
    if state.get("reset_requested"):
        return "reset_session"

    session = state["session"]
    if not session.checklist_sent:
        return "send_checklist"
    return "ingest_message"


def route_after_ingest(state: Dict[str, Any]) -> str:
    if state.get("explicit_run_requested") and not state.get("has_minimum_runnable_info"):
        return "send_minimum_required"

    session = state["session"]
    if state.get("explicit_run_requested") and state.get("has_minimum_runnable_info"):
        return "start_analysis"

    if state.get("has_minimum_runnable_info") and not state.get("missing_fields"):
        return "start_analysis"

    session.status = "awaiting_run_confirmation"
    return "send_follow_up"


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
        response = workflow._response(
            session,
            [{"type": "text", "content": content}],
        )
        return {"session": session, "status": session.status, "response": response}

    return node


def make_send_follow_up_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        session.status = "awaiting_run_confirmation"
        workflow.session_manager.save(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": workflow.session_manager.build_follow_up_text(session)}],
        )
        return {"session": session, "status": session.status, "response": response}

    return node


def make_send_minimum_required_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        session.status = "awaiting_run_confirmation"
        workflow.session_manager.save(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": "当前信息仍不足以运行，请至少补充产品名称、品类、核心卖点、价格状态和包装信息。"}],
        )
        return {"session": session, "status": session.status, "response": response}

    return node


def make_start_analysis_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        session.partial_run_authorized = bool(state.get("explicit_run_requested"))
        session.status = "running"
        session.last_task_id = f"{session.session_id}__run"
        workflow.session_manager.save(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": "信息已收齐到当前可运行程度，开始分析。完成后我会回传简版结论和 HTML 报告。"}],
            task_id=session.last_task_id,
        )
        return {"session": session, "status": session.status, "task_id": session.last_task_id, "response": response}

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
        response = workflow._response(
            session,
            [{"type": "text", "content": "绯荤粺鍦ㄥ鐞嗕换鍔℃椂鍑虹幇寮傚父锛岃绋嶅悗閲嶈瘯銆?"}],
        )
        return {"session": session, "status": session.status, "response": response}

    return node


def make_load_task_session_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        task_id = state["task_id"]
        session_id = task_id.rsplit("__run", 1)[0]
        session = workflow.session_manager.load(session_id)
        return {"session": session}

    return node


def make_build_concept_payload_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        payload = workflow.session_manager.build_concept_payload(state["session"])
        return {"concept_payload": payload}

    return node


def make_build_concept_input_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        payload = state["concept_payload"]
        concept_input = workflow.concept_input_cls(
            concept_name=payload["concept_name"],
            brand=payload["brand"],
            category=payload["category"],
            price=payload["price"],
            core_claims=payload["core_claims"],
            packaging_summary=payload["packaging_summary"],
            tagline=payload.get("tagline", ""),
            target_channels=payload.get("target_channels", []),
            competitive_anchors=payload.get("competitive_anchors", []),
            context_notes=payload.get("context_notes", ""),
        )
        return {"concept_input": concept_input}

    return node


def make_run_single_concept_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        packaging_image_path = state["concept_payload"].get("packaging_image_path", "")
        if packaging_image_path:
            packaging_review = workflow.advanced_runner.run_packaging_review(
                state["concept_input"],
                packaging_image_path,
            )
            report = packaging_review["single_concept_report"]
            report["appendix"]["packaging_review"] = packaging_review["packaging_review"]
        else:
            report = workflow.runner.run(state["concept_input"])

        report["input_summary"]["missing_fields"] = state["concept_payload"]["missing_fields"]
        report["input_summary"]["packaging_image_path"] = packaging_image_path
        report = workflow.runner.refresh_report_business_fields(report)
        return {"report": report}

    return node


def make_render_html_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        html = workflow.renderer.render(state["report"])
        return {"html": html}

    return node


def make_persist_outputs_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        task_id = session.last_task_id or state["task_id"]
        json_path = workflow.output_dir / f"{task_id}.json"
        html_path = workflow.output_dir / f"{task_id}.html"

        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(state["report"], handle, ensure_ascii=False, indent=2)
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(state["html"])

        session.status = "completed"
        session.html_report_path = str(html_path)
        session.json_report_path = str(json_path)
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
            [{"type": "text", "content": f"简版结论：{summary}"}],
            html_report_path=session.html_report_path,
            json_report_path=session.json_report_path,
            public_report_url=state.get("public_report_url", ""),
        )
        return {"response": response}

    return node
