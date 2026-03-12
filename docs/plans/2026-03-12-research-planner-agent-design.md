# Research Planner Agent Design

**Date:** 2026-03-12

## Goal

Extend the current 9-agent qualitative assistant so the research assistant works in two phases:

- a front-stage planning phase that decomposes the user request, identifies intent, detects missing information, and decides whether clarification is required
- a back-stage synthesis phase that summarizes the mother-agent outputs into the fixed research template

This closes the current product gap where the system can summarize responses, but cannot first act like a researcher who understands what to study and what information is still missing.

## Confirmed Product Decisions

- Keep the existing 8 mother personas already stored in `persona_samples_complete.json`.
- Keep DingTalk, HTML, and JSON outputs as the successful output shell.
- Add a planner stage before mother-agent execution.
- The planner must identify user intent and decompose the research task before any mother-agent run.
- If the planner decides the brief is not yet runnable, the system must ask follow-up questions first.
- Only if the user explicitly authorizes it may the system run with assumptions before all information is complete.
- If a run proceeds under assumptions, those assumptions must be visible in the report.
- Mother agents should receive both the original brief and the planner-produced research task card.
- The final research assistant may use both the original brief and the planner output, but its reasoning should still be mainly grounded in the mother-agent outputs.

## Current Gap

The current `qualitative_research.py` implements only:

- mother-agent execution
- research-assistant summary

It does not implement:

- intent recognition by a dedicated planner agent
- request decomposition into research objectives and evaluation dimensions
- missing-information detection
- planner-generated clarification questions
- authorization logic for assumption-based runs

This means the current workflow still behaves like a structured execution engine, not like a research assistant that first understands the assignment.

## Target Architecture

The shell remains the same:

- `dingtalk_bot.py`
- `langgraph_flows.py`
- `langgraph_nodes.py`
- `task_session_manager.py`
- `html_report_renderer.py`
- `ai_clients.py`

The qualitative domain layer becomes a two-stage assistant workflow:

1. `ResearchPlannerAgent`
2. `MomPersonaAgent` x 8 or x 1
3. `ResearchAssistantAgent`

## Research Planner Agent

### Responsibility

The planner is the first LLM agent that sees the current task session.

It must:

- identify what the user really wants to learn
- normalize the task into one of the supported qualitative question types
- recommend single or multi mode
- identify the likely target persona if single mode is implied
- extract the core research objectives
- define the evaluation dimensions the mother agents should answer against
- identify what information is still missing
- generate the next clarification questions
- decide whether the task is runnable now
- define the assumptions that would be used if the user explicitly authorizes an early run

### Required Output Schema

The planner must return strict JSON:

```json
{
  "normalized_intent": "...",
  "question_type": "product_concept|purchase_decision|needs_pain_points|copy_feedback",
  "recommended_mode": "multi|single",
  "target_persona": "",
  "research_objectives": ["..."],
  "evaluation_dimensions": ["..."],
  "required_materials": ["..."],
  "missing_information": ["..."],
  "clarification_questions": ["..."],
  "assumptions_if_run_now": ["..."],
  "is_runnable": false,
  "needs_clarification": true
}
```

### Validation Rules

- all keys are required
- all list fields must contain at least one item except `missing_information` and `assumptions_if_run_now`, which may be empty only when appropriate
- `question_type` must be one of the supported values
- `recommended_mode` must be `single` or `multi`
- if `recommended_mode = single`, `target_persona` should be populated whenever the user has clearly pointed to one persona
- if `needs_clarification = true`, `clarification_questions` must not be empty
- if `is_runnable = false`, the workflow must not dispatch mother agents unless the user explicitly authorizes an assumptions-based run

## Workflow and State Changes

The DingTalk flow changes from:

1. collect fields
2. run mothers
3. summarize

to:

1. collect raw user input
2. run planner agent
3. if clarification is needed, stop and ask follow-up questions
4. if runnable, wait for run confirmation or continue according to workflow rules
5. dispatch mother agents using the planner-generated task card
6. run the final research assistant summary

Recommended session states:

- `collecting_raw_input`
- `planning`
- `awaiting_clarification`
- `awaiting_run_confirmation`
- `running`
- `completed`
- `error`

## Authorization Rule

The planner is strict by default:

- if the brief is incomplete, it asks for clarification
- it does not assume permission to proceed

Only after explicit user language such as:

- `先跑一次`
- `按当前信息先看`
- `先假设着跑`
- `先基于现有资料跑一版`

may the workflow continue with `assumptions_if_run_now`.

When that happens:

- the planner output should be preserved in the report
- the assumption list should be visible to the user
- the mother agents should receive those assumptions as part of the task card

## Mother-Agent Input Contract

Mother agents should no longer consume only the raw brief. Each mother agent must receive:

- the original brief
- the planner output
- the explicit evaluation dimensions
- the assumptions, if the user authorized an assumption-based run

This ensures the eight responses stay aligned to the same research task rather than drifting into parallel but inconsistent interpretations.

## Final Research Assistant Contract

The synthesis assistant remains the last step, but it now sees three inputs:

- original brief
- planner output
- validated mother-agent responses

Its public summary template stays unchanged:

- `consensus`
- `differences`
- `pain_points`
- `drivers`
- `barriers`
- `copy_insights`
- `recommendations`

The reasons in that summary should still come mainly from the mother-agent responses, not from the planner alone.

## Output Changes

Successful output should add a visible planning layer.

Recommended report layers:

1. Task decomposition
   - normalized intent
   - research objectives
   - evaluation dimensions
   - missing information
   - assumptions used for the run, if any

2. Consumer voice
   - 8 mother responses or 1 mother response

3. Research summary
   - the fixed final summary template

Recommended JSON addition:

```json
{
  "research_plan": {
    "normalized_intent": "...",
    "question_type": "...",
    "recommended_mode": "...",
    "target_persona": "",
    "research_objectives": ["..."],
    "evaluation_dimensions": ["..."],
    "required_materials": ["..."],
    "missing_information": ["..."],
    "clarification_questions": ["..."],
    "assumptions_if_run_now": ["..."],
    "is_runnable": true,
    "needs_clarification": false
  }
}
```

## Failure Handling

Planner failure is a hard failure just like mother-agent or summary-agent failure.

Rejected states include:

- planner LLM call fails
- planner returns fallback mode
- planner returns invalid JSON
- planner schema is incomplete
- planner says the task is not runnable, but the workflow still tries to run without explicit user authorization

These should not create a fake completed report.

## Testing Strategy

### Planner runner tests

- planner executes before any mother-agent call
- planner output is validated strictly
- planner can block execution and return clarification requirements
- user authorization enables an assumptions-based run
- mother agents receive planner output as part of their prompt context

### Session and workflow tests

- unclear user requests move the session into `awaiting_clarification`
- clarification text shown to DingTalk comes from planner output rather than only field-template gaps
- explicit authorization changes the workflow from blocked to runnable

### Rendering tests

- HTML includes a task decomposition section
- assumption-based runs show the assumptions clearly
- successful reports preserve both the consumer voice layer and the final summary layer

## Implementation Notes

- Keep the existing fixed final summary schema.
- Do not let the planner silently auto-fill missing high-stakes information without user authorization.
- Treat planner output as first-class structured state, not temporary prompt text.
- Preserve backward compatibility for old session files where possible, but normalize them into the new qualitative workflow state model.
