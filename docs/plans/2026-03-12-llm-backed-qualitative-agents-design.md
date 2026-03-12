# LLM-Backed Qualitative Agents Design

**Date:** 2026-03-12

## Goal

Replace the current template-driven qualitative runner with a real 9-agent LLM workflow:

- 8 mother persona agents each produce their own response through a separate LLM call.
- 1 research assistant agent summarizes those responses through its own LLM call.
- Any agent failure makes the whole run incomplete. No partial consumer voice or partial summary should be returned to DingTalk.

## Confirmed Product Decisions

- Reuse the existing 8 mother personas already stored in `persona_samples_complete.json`.
- Keep the existing DingTalk entrypoint, HTML output, and JSON output contract on successful runs.
- Mother persona output must include both a consumer-sounding original answer and a small set of structured fields.
- The research assistant may see both the original research brief and the mother-agent outputs.
- The research assistant's reasoning should primarily be grounded in the 8 mother-agent outputs.
- The summary template stays fixed:
  - `consensus`
  - `differences`
  - `pain_points`
  - `drivers`
  - `barriers`
  - `copy_insights`
  - `recommendations`
- If any mother agent or the research assistant agent fails, DingTalk should only return `本次结果不完整，请稍后重试`.
- Failed runs must not return partial mother responses and must not present a fake complete report.

## Current Gap

`qualitative_research.py` currently does not implement real agent orchestration. It builds persona responses and the research summary through deterministic local string templates. The `ai_client` is passed into the qualitative runner, but the active qualitative path does not use it to generate the mother responses or the research assistant summary.

This means the current system is not a true 9-agent LLM workflow and does not satisfy the product contract.

## Architecture

The DingTalk and LangGraph shell stays in place. The qualitative domain layer is refactored into explicit agent orchestration.

### Keep

- `dingtalk_stream_service.py`
- `langgraph_flows.py`
- `langgraph_nodes.py`
- `dingtalk_bot.py`
- `task_session_manager.py`
- `html_report_renderer.py`
- `persona_samples_complete.json`
- `ai_clients.py`

### Rewrite in the domain layer

- `qualitative_research.py`

`qualitative_research.py` should become the source of truth for:

- research brief normalization
- mother persona agent prompt building
- research assistant agent prompt building
- structured JSON parsing
- schema validation
- failure gating
- final report assembly

## Agent Model

### 1. Mother Persona Agent

Each selected mother persona is represented by a dedicated LLM call.

Input to each mother agent:

- the persona record from `persona_samples_complete.json`
- the normalized research brief
- output rules requiring consumer voice rather than analyst language
- a strict JSON schema

Required output fields:

- `persona_id`
- `persona_name`
- `stance`
- `core_needs`
- `motivations`
- `concerns`
- `decision_logic`
- `verbatim_answer`
- `evidence_trace`

Field rules:

- `verbatim_answer` is the externally displayed answer and must sound like real consumer voice.
- `evidence_trace` is internal support for the research assistant and should explain why this persona landed on the answer.
- `persona_id` must match the persona being executed. Mismatches are failures.

### 2. Research Assistant Agent

The research assistant runs only after all required mother agents succeed.

Input to the research assistant:

- the normalized research brief
- the full set of validated mother-agent outputs

Prompt rule:

- the assistant may use the brief for context
- the assistant should ground its reasons mainly in the mother-agent outputs
- it must not invent conclusions unsupported by those outputs

Required output fields:

- `consensus`
- `differences`
- `pain_points`
- `drivers`
- `barriers`
- `copy_insights`
- `recommendations`

In single mode the same schema is used, but the summary must make clear that the result is based on one persona only.

## LLM Contract

The runner must treat this as a hard LLM-backed workflow rather than a best-effort workflow.

### Allowed success path

- `ai_client` is configured
- every mother agent returns valid JSON
- every required field is present
- every field type is correct
- the research assistant returns valid JSON in the fixed schema

### Rejected states

- `ai_client` missing or unconfigured
- any LLM call raises an exception
- `generate_text()` returns fallback mode
- non-JSON output
- JSON parsing failure
- missing required fields
- persona mismatch
- structurally empty summary sections

Any rejected state should raise a domain error such as `IncompleteResearchRunError`.

## Failure Handling

Failure behavior is strict:

- stop the run immediately when a required agent fails
- do not return partial mother outputs
- do not generate a public-facing HTML or JSON success report
- set the workflow response to an error state
- return only `本次结果不完整，请稍后重试`

Internal diagnostics may still be logged for debugging, but they are not shown as user-facing report content.

## Output Schema

Successful runs should keep the current two-layer output, but the values must now come from real LLM agent calls.

Recommended successful result shape:

```json
{
  "meta": {
    "mode": "multi",
    "question_type": "copy_feedback",
    "generated_at": "2026-03-12 10:30:00",
    "total_agents": 8,
    "agent_count_expected": 8,
    "agent_count_completed": 8,
    "completion_status": "complete"
  },
  "research_brief": {
    "user_question": "...",
    "product_info": "...",
    "copy_material": "...",
    "background_material": "..."
  },
  "consumer_voice": [
    {
      "persona_id": "M03",
      "persona_name": "丁小红",
      "stance": "hesitant",
      "core_needs": ["..."],
      "motivations": ["..."],
      "concerns": ["..."],
      "decision_logic": "...",
      "verbatim_answer": "...",
      "evidence_trace": "..."
    }
  ],
  "research_summary": {
    "consensus": ["..."],
    "differences": ["..."],
    "pain_points": ["..."],
    "drivers": ["..."],
    "barriers": ["..."],
    "copy_insights": ["..."],
    "recommendations": ["..."]
  },
  "appendix": {
    "selected_persona": null,
    "follow_up_context": "",
    "attachments": []
  }
}
```

Failure runs should not masquerade as successful reports.

## DingTalk and Workflow Behavior

The DingTalk workflow remains the same up to the point where analysis starts. The change is in the run phase:

1. collect the research brief
2. build the qualitative request
3. execute 8 or 1 mother LLM calls
4. validate all mother outputs
5. execute the research assistant LLM call
6. validate the summary output
7. render JSON + HTML and return the usual report links

If step 3 to 6 fails:

- mark the session as `error`
- return only `本次结果不完整，请稍后重试`
- do not expose partial content

## Testing Strategy

### Runner tests

- multi mode performs 8 mother-agent LLM calls plus 1 research-assistant call
- single mode performs 1 mother-agent LLM call plus 1 research-assistant call
- valid mocked LLM JSON produces the expected report schema
- fallback LLM mode raises an incomplete-run error
- invalid JSON raises an incomplete-run error
- persona mismatch raises an incomplete-run error

### Workflow tests

- successful DingTalk flow still produces HTML and JSON outputs
- failed agent runs return only the incomplete-result message
- failed agent runs do not return partial consumer voice

### Stream-service tests

- DingTalk stream handler sends the incomplete-result message when the workflow reports error
- successful runs still send the markdown completion message with the report link

## Implementation Notes

- Keep the persona assets unchanged unless the schema is proven unusable.
- Prefer strict validation over permissive repair.
- Do not silently fall back to deterministic template text.
- Keep the successful output contract stable for DingTalk and HTML consumers.
