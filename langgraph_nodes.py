import json
from typing import Any, Dict


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


def route_after_detect_command(state: Dict[str, Any]) -> str:
    if state.get("reset_requested"):
        return "reset_session"
    if not state["session"].checklist_sent:
        return "send_checklist"
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

        workflow.session_manager.update_from_message(session, text, attachments=attachments)
        session = workflow.session_manager.load(session.session_id)
        explicit_run_requested = workflow.session_manager.has_run_confirmation(text)
        has_minimum = workflow.session_manager.has_minimum_runnable_info(session)
        missing_fields = list(session.missing_fields)

        return {
            "session": session,
            "explicit_run_requested": explicit_run_requested,
            "allow_assumption_run": session.allow_assumption_run,
            "has_minimum_runnable_info": has_minimum,
            "missing_fields": missing_fields,
        }

    return node


def route_after_ingest(state: Dict[str, Any]) -> str:
    if state.get("explicit_run_requested") and state.get("has_minimum_runnable_info"):
        return "plan_research"
    return "send_follow_up"


def make_plan_research_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        payload = workflow.session_manager.build_research_input_payload(session)
        research_input = workflow.research_input_cls(**payload)
        research_plan = workflow.runner.plan(research_input)
        session.planner_result = research_plan
        workflow.session_manager.save(session)
        return {
            "session": session,
            "research_plan": research_plan,
            "planner_requires_clarification": bool(research_plan.get("needs_clarification")),
            "allow_assumption_run": session.allow_assumption_run,
        }

    return node


def route_after_planning(state: Dict[str, Any]) -> str:
    if state.get("planner_requires_clarification") and not state.get("allow_assumption_run"):
        return "send_follow_up"
    return "start_analysis"


def make_send_follow_up_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        if state.get("planner_requires_clarification"):
            session.status = "awaiting_clarification"
        else:
            session.status = "collecting" if state.get("missing_fields") else "awaiting_run_confirmation"
        workflow.session_manager.save(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": workflow.session_manager.build_follow_up_text(session)}],
        )
        return {"session": session, "status": session.status, "response": response}

    return node


def make_start_analysis_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        session = state["session"]
        session.partial_run_authorized = bool(state.get("allow_assumption_run"))
        session.status = "running"
        session.last_task_id = f"{session.session_id}__run"
        workflow.session_manager.save(session)
        response = workflow._response(
            session,
            [{"type": "text", "content": "研究任务已收齐，开始生成妈妈原声与研究总结。"}],
            task_id=session.last_task_id,
        )
        return {
            "session": session,
            "status": session.status,
            "task_id": session.last_task_id,
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
        return {"session": session}

    return node


def make_build_research_input_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        payload = workflow.session_manager.build_research_input_payload(state["session"])
        research_input = workflow.research_input_cls(**payload)
        return {"research_input_payload": payload, "research_input": research_input}

    return node


def make_run_research_node(workflow):
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        report = workflow.runner.run(state["research_input"])
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
            [{"type": "text", "content": f"简版结论：{summary}"}],
            html_report_path=session.html_report_path,
            json_report_path=session.json_report_path,
            public_report_url=state.get("public_report_url", ""),
        )
        return {"response": response}

    return node
