from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from backend.workflow.langgraph_nodes import (
    make_build_business_brief_node,
    make_build_research_input_node,
    make_detect_command_node,
    make_finalize_task_response_node,
    make_ingest_message_node,
    make_load_session_node,
    make_load_task_session_node,
    make_persist_outputs_node,
    make_prompt_shield_node,
    make_publish_report_node,
    make_readiness_gate_node,
    make_render_html_node,
    make_reset_session_node,
    make_run_research_node,
    make_send_checklist_node,
    make_send_follow_up_node,
    make_start_analysis_node,
    make_workflow_error_node,
    route_after_detect_command,
    route_after_prompt_shield,
    route_after_readiness_gate,
)
from backend.workflow.langgraph_state import AnalysisGraphState, DingTalkWorkflowState

import logging

logger = logging.getLogger(__name__)


def _wrap_with_error_boundary(node_fn):
    """Wrap a node function to catch exceptions and set error_detected flag."""
    def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return node_fn(state)
        except Exception as exc:
            logger.exception("Node error caught by error boundary: %s", exc)
            return {"error_detected": True, "error_message": str(exc)}
    return wrapper


def _route_error_or_continue(state: Dict[str, Any]) -> str:
    """Route to error node if error_detected, otherwise continue normal flow."""
    if state.get("error_detected"):
        return "error"
    return "continue"


def build_analysis_graph(workflow):
    graph = StateGraph(AnalysisGraphState)
    graph.add_node("run_research", make_run_research_node(workflow))
    graph.add_edge(START, "run_research")
    graph.add_edge("run_research", END)
    return graph.compile()


def build_dingtalk_workflow_graph(workflow):
    graph = StateGraph(DingTalkWorkflowState)
    graph.add_node("load_session", make_load_session_node(workflow))
    graph.add_node("prompt_shield", make_prompt_shield_node(workflow))
    graph.add_node("detect_command", make_detect_command_node(workflow))
    graph.add_node("reset_session", make_reset_session_node(workflow))
    graph.add_node("send_checklist", make_send_checklist_node(workflow))
    graph.add_node("ingest_message", _wrap_with_error_boundary(make_ingest_message_node(workflow)))
    graph.add_node("readiness_gate", _wrap_with_error_boundary(make_readiness_gate_node(workflow)))
    graph.add_node("build_business_brief", _wrap_with_error_boundary(make_build_business_brief_node(workflow)))
    graph.add_node("send_follow_up", make_send_follow_up_node(workflow))
    graph.add_node("start_analysis", _wrap_with_error_boundary(make_start_analysis_node(workflow)))
    graph.add_node("error", make_workflow_error_node(workflow))

    # START → load_session → prompt_shield → (reject | detect_command)
    graph.add_edge(START, "load_session")
    graph.add_edge("load_session", "prompt_shield")
    graph.add_conditional_edges(
        "prompt_shield",
        route_after_prompt_shield,
        {
            "end": END,
            "continue": "detect_command",
        },
    )
    graph.add_conditional_edges(
        "detect_command",
        route_after_detect_command,
        {
            "reset_session": "reset_session",
            "send_checklist": "send_checklist",
            "ingest_message": "ingest_message",
        },
    )
    graph.add_edge("reset_session", "send_checklist")

    # ingest_message → (error | readiness_gate)
    graph.add_conditional_edges(
        "ingest_message",
        _route_error_or_continue,
        {
            "error": "error",
            "continue": "readiness_gate",
        },
    )
    # readiness_gate → (error | build_business_brief | send_follow_up)
    def _route_readiness(state):
        if state.get("error_detected"):
            return "error"
        return route_after_readiness_gate(state)
    graph.add_conditional_edges(
        "readiness_gate",
        _route_readiness,
        {
            "error": "error",
            "build_business_brief": "build_business_brief",
            "send_follow_up": "send_follow_up",
        },
    )
    # build_business_brief → (error | start_analysis)
    graph.add_conditional_edges(
        "build_business_brief",
        _route_error_or_continue,
        {
            "error": "error",
            "continue": "start_analysis",
        },
    )
    # start_analysis → (error | END)
    graph.add_conditional_edges(
        "start_analysis",
        _route_error_or_continue,
        {
            "error": "error",
            "continue": END,
        },
    )

    graph.add_edge("send_checklist", END)
    graph.add_edge("send_follow_up", END)
    graph.add_edge("error", END)
    return graph.compile()


def build_dingtalk_task_graph(workflow):
    graph = StateGraph(DingTalkWorkflowState)
    graph.add_node("load_task_session", make_load_task_session_node(workflow))
    graph.add_node("build_research_input", make_build_research_input_node(workflow))
    graph.add_node("run_research", make_run_research_node(workflow))
    graph.add_node("render_html", make_render_html_node(workflow))
    graph.add_node("persist_outputs", make_persist_outputs_node(workflow))
    graph.add_node("publish_report", make_publish_report_node(workflow))
    graph.add_node("finalize_task_response", make_finalize_task_response_node(workflow))

    graph.add_edge(START, "load_task_session")
    graph.add_edge("load_task_session", "build_research_input")
    graph.add_edge("build_research_input", "run_research")
    graph.add_edge("run_research", "render_html")
    graph.add_edge("render_html", "persist_outputs")
    graph.add_edge("persist_outputs", "publish_report")
    graph.add_edge("publish_report", "finalize_task_response")
    graph.add_edge("finalize_task_response", END)
    return graph.compile()
