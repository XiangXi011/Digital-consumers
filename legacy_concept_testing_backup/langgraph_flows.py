from langgraph.graph import END, START, StateGraph

from langgraph_nodes import (
    make_build_concept_input_node,
    make_build_concept_payload_node,
    make_build_product_node,
    make_build_report_node,
    make_detect_command_node,
    make_evaluate_batch_node,
    make_finalize_task_response_node,
    make_ingest_message_node,
    make_load_session_node,
    make_load_task_session_node,
    make_persist_outputs_node,
    make_publish_report_node,
    make_prepare_discussion_node,
    make_render_html_node,
    make_reset_session_node,
    make_run_deep_dives_node,
    make_run_discussion_node,
    make_run_single_concept_node,
    make_send_checklist_node,
    make_send_follow_up_node,
    make_send_minimum_required_node,
    make_start_analysis_node,
    make_workflow_error_node,
    route_after_detect_command,
    route_after_ingest,
)
from langgraph_state import AnalysisGraphState, DingTalkWorkflowState


def build_analysis_graph(runner):
    graph = StateGraph(AnalysisGraphState)
    graph.add_node("build_product", make_build_product_node())
    graph.add_node("evaluate_batch", make_evaluate_batch_node(runner))
    graph.add_node("prepare_discussion", make_prepare_discussion_node(runner))
    graph.add_node("run_discussion", make_run_discussion_node(runner))
    graph.add_node("run_deep_dives", make_run_deep_dives_node(runner))
    graph.add_node("build_report", make_build_report_node(runner))

    graph.add_edge(START, "build_product")
    graph.add_edge("build_product", "evaluate_batch")
    graph.add_edge("evaluate_batch", "prepare_discussion")
    graph.add_edge("prepare_discussion", "run_discussion")
    graph.add_edge("run_discussion", "run_deep_dives")
    graph.add_edge("run_deep_dives", "build_report")
    graph.add_edge("build_report", END)
    return graph.compile()


def build_dingtalk_workflow_graph(workflow):
    graph = StateGraph(DingTalkWorkflowState)
    graph.add_node("load_session", make_load_session_node(workflow))
    graph.add_node("detect_command", make_detect_command_node(workflow))
    graph.add_node("reset_session", make_reset_session_node(workflow))
    graph.add_node("ingest_message", make_ingest_message_node(workflow))
    graph.add_node("send_checklist", make_send_checklist_node(workflow))
    graph.add_node("send_follow_up", make_send_follow_up_node(workflow))
    graph.add_node("send_minimum_required", make_send_minimum_required_node(workflow))
    graph.add_node("start_analysis", make_start_analysis_node(workflow))
    graph.add_node("error", make_workflow_error_node(workflow))

    graph.add_edge(START, "load_session")
    graph.add_edge("load_session", "detect_command")
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
    graph.add_conditional_edges(
        "ingest_message",
        route_after_ingest,
        {
            "send_follow_up": "send_follow_up",
            "send_minimum_required": "send_minimum_required",
            "start_analysis": "start_analysis",
        },
    )
    graph.add_edge("send_checklist", END)
    graph.add_edge("send_follow_up", END)
    graph.add_edge("send_minimum_required", END)
    graph.add_edge("start_analysis", END)
    graph.add_edge("error", END)
    return graph.compile()


def build_dingtalk_task_graph(workflow):
    graph = StateGraph(DingTalkWorkflowState)
    graph.add_node("load_task_session", make_load_task_session_node(workflow))
    graph.add_node("build_concept_payload", make_build_concept_payload_node(workflow))
    graph.add_node("build_concept_input", make_build_concept_input_node(workflow))
    graph.add_node("run_single_concept", make_run_single_concept_node(workflow))
    graph.add_node("render_html", make_render_html_node(workflow))
    graph.add_node("persist_outputs", make_persist_outputs_node(workflow))
    graph.add_node("publish_report", make_publish_report_node(workflow))
    graph.add_node("finalize_task_response", make_finalize_task_response_node(workflow))

    graph.add_edge(START, "load_task_session")
    graph.add_edge("load_task_session", "build_concept_payload")
    graph.add_edge("build_concept_payload", "build_concept_input")
    graph.add_edge("build_concept_input", "run_single_concept")
    graph.add_edge("run_single_concept", "render_html")
    graph.add_edge("render_html", "persist_outputs")
    graph.add_edge("persist_outputs", "publish_report")
    graph.add_edge("publish_report", "finalize_task_response")
    graph.add_edge("finalize_task_response", END)
    return graph.compile()
