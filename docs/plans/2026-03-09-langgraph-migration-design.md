# LangGraph Migration Design

## Goal

Replace the current hand-written workflow orchestration with LangGraph across the full consumer testing flow, while preserving the existing persona engine, scoring behavior, report structure, and HTML rendering.

## Scope

This migration covers:

- DingTalk-style conversation orchestration
- Session loading, field ingestion, missing-field follow-up, and partial-run authorization
- Single-concept analysis orchestration
- A/B comparison, price ladder, and packaging review orchestration
- Final short summary + HTML/JSON report output

This migration does not replace:

- Persona generation rules
- Legacy digital consumer simulation engine
- HTML report visual design
- OpenAI-compatible client integration

## Architecture

### 1. Main Graph

The main graph handles conversation and execution state for a single task request.

Nodes:

- `load_session_node`
- `ingest_message_node`
- `send_checklist_node`
- `send_follow_up_node`
- `start_analysis_node`
- `run_analysis_subgraph`
- `finalize_response_node`
- `error_node`

Routing:

- first contact -> checklist
- incomplete info without authorization -> follow-up
- complete info -> analysis
- incomplete info with explicit authorization -> analysis
- unrecoverable exception -> error

### 2. Analysis Subgraph

The analysis subgraph handles deterministic execution for a single concept report.

Nodes:

- `build_concept_input_node`
- `evaluate_batch_node`
- `run_discussion_node`
- `run_deep_dive_node`
- `build_report_node`
- `render_html_node`
- `persist_outputs_node`

This subgraph will reuse the current report-building logic and the legacy orchestrator.

### 3. Advanced Analysis

`advanced_testing.py` will stop acting as the primary orchestration layer. Instead it will call the analysis graph or specialized wrappers built on top of the graph state and reusable report primitives.

## State Model

Use a single shared typed state structure for both the main graph and analysis subgraph.

Core fields:

- `session_id`
- `group_id`
- `conversation_id`
- `user_id`
- `status`
- `event`
- `task_id`
- `fields`
- `missing_fields`
- `partial_run_authorized`
- `reply_messages`
- `concept_payload`
- `concept_input`
- `product`
- `evaluation_results`
- `discussion`
- `deep_dives`
- `report`
- `html`
- `html_report_path`
- `json_report_path`
- `error`

## File Plan

### New files

- `langgraph_state.py`
- `langgraph_nodes.py`
- `langgraph_flows.py`

### Refactored files

- `concept_testing.py`
- `advanced_testing.py`
- `dingtalk_bot.py`
- `run_dingtalk_demo.py`
- `tests/test_concept_testing.py`
- `tests/test_advanced_testing.py`
- `tests/test_dingtalk_workflow.py`

### Reused files

- `task_session_manager.py`
- `html_report_renderer.py`
- `ai_clients.py`
- `digital_consumer_agents(1).py`

## Error Handling

- Node-level exceptions are converted into graph state `error`
- Main graph routes failures to `error_node`
- Packaging image analysis remains safely degradable
- Missing minimum runnable fields never enter analysis

## Testing Strategy

1. Add failing tests for LangGraph-based conversation routing
2. Add failing tests for LangGraph-backed single concept execution
3. Implement minimal graph state and graph builder
4. Migrate existing entrypoints to graph execution
5. Re-run the full test suite
6. Run the local DingTalk demo end-to-end

## Migration Constraints

- Preserve public behavior where possible
- Keep JSON/HTML output paths stable
- Avoid rewriting report semantics unless required by graph interfaces
- Prefer minimal LangGraph `StateGraph` primitives over deeper abstractions
