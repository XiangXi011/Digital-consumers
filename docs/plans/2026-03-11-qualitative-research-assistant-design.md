# Qualitative Research Assistant Design

**Date:** 2026-03-11

## Goal

Replace the current concept-testing workflow with a 9-agent qualitative research assistant:

- 8 mother persona agents reuse the existing persona library and answer from their own perspective.
- 1 research assistant agent summarizes those answers into a fixed research template.
- The primary delivery contract stays the same: DingTalk message, HTML report, and JSON result.

## Confirmed Product Decisions

- Reuse the current 8 mother personas instead of redefining them.
- Replace the old primary workflow instead of running both systems side by side.
- Keep a full backup of the legacy concept-testing implementation in a new folder before changing behavior.
- Support both natural-language input and semi-structured input.
- Use semi-structured input when available, and ask a follow-up only when mode or persona cannot be inferred safely.
- Keep two modes:
  - `multi`: all 8 mother agents answer the same question.
  - `single`: one specified mother agent answers and can be followed up further.
- Keep four research question families:
  - product concept
  - purchase decision
  - needs / pain points
  - copy / selling point feedback
- Keep the research assistant output in a limited fixed template:
  - consensus
  - differences
  - pain points
  - drivers
  - barriers
  - copy insights
  - recommendations

## Architecture

The outer shell stays in place and the middle of the system is replaced.

### Keep

- `dingtalk_stream_service.py`
- `report_publisher.py`
- `ai_clients.py`
- the current persona assets in `persona_samples_complete.json`

### Rewrite

- `task_session_manager.py`
- `langgraph_state.py`
- `langgraph_nodes.py`
- `langgraph_flows.py`
- `dingtalk_bot.py`
- `html_report_renderer.py`
- the report-oriented tests

### Add

- `qualitative_research.py`

`qualitative_research.py` becomes the new domain layer and contains:

- the request schema for a research brief
- the persona loading and persona selection logic
- mother-agent response generation
- research-assistant summarization
- final report assembly

## Research Brief and Session Model

The old session model is centered on concept-testing fields such as price, packaging, and claims. The new model should collect a research brief that works across all four research question families.

### Required Session Fields

- `mode`
- `question_type`
- `user_question`

### Conditionally Required Session Fields

- `persona_id` for single mode only

### Optional Supporting Fields

- `background_material`
- `product_info`
- `copy_material`
- `attachments`
- `follow_up_context`

### Input Rules

- If the user explicitly writes `多人` or `单人`, trust that mode.
- If the user names one persona, default to single mode.
- If the question clearly asks for comparison across mothers, default to multi mode.
- If single mode is clear but no persona is specified, ask one follow-up.
- If the question type cannot be inferred reliably, ask one follow-up.
- Follow-up analysis should reuse the same session rather than starting a new task.

## Agent Orchestration

The qualitative workflow should be a two-stage pipeline.

### Stage 1: Mother Persona Responses

Each selected mother agent receives the same research brief and returns a structured response with both reasoning signals and a consumer-sounding answer.

Required response fields:

- `persona_id`
- `persona_name`
- `question_type`
- `stance`
- `core_needs`
- `motivations`
- `concerns`
- `decision_logic`
- `verbatim_answer`
- `confidence_note`

The critical rule is that `verbatim_answer` reads like consumer voice, while the other fields make downstream summarization deterministic.

### Stage 2: Research Assistant Summary

The research assistant consumes the selected mother-agent responses and returns a fixed template:

- `consensus`
- `differences`
- `pain_points`
- `drivers`
- `barriers`
- `copy_insights`
- `recommendations`

Single mode still uses the same schema. In that case the summary must explicitly note that the result is based on one persona and should not be treated as group consensus.

## Output Schema

The JSON result becomes the source of truth for both DingTalk summaries and HTML rendering.

```json
{
  "meta": {
    "mode": "multi",
    "question_type": "purchase_decision",
    "generated_at": "2026-03-11 18:30:00",
    "total_agents": 8
  },
  "research_brief": {
    "user_question": "...",
    "product_info": "...",
    "copy_material": "...",
    "background_material": "..."
  },
  "consumer_voice": [
    {
      "persona_id": "M01",
      "persona_name": "Chong'ai Fuyang Ma",
      "stance": "interested_but_concerned",
      "core_needs": ["..."],
      "motivations": ["..."],
      "concerns": ["..."],
      "decision_logic": "...",
      "verbatim_answer": "...",
      "confidence_note": "..."
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

## DingTalk and HTML Reporting

The DingTalk completion message should remain brief and stable:

- one short research-assistant conclusion
- the active mode
- the covered persona or persona list
- report links or file paths using the existing contract

The HTML report should be rebuilt around two layers:

1. consumer voice
2. research summary

Recommended sections:

- task overview
- mode and question type
- original user question and supporting materials
- mother persona response cards
- research assistant summary blocks
- appendix and follow-up context

The new report must not present the old quantitative fields such as conversion estimates, segment opportunity tables, or launch recommendations.

## LangGraph Shape

The analysis graph becomes simpler than the current concept-testing graph.

Recommended analysis steps:

1. build research brief
2. select mother agents
3. run mother responses
4. generate research summary
5. assemble final report
6. render HTML
7. persist JSON and HTML
8. publish report URL if configured

The DingTalk workflow graph still handles:

- session loading
- reset handling
- information collection
- run confirmation
- async task execution

## Migration and Backup Strategy

Before any rewrite, copy the legacy concept-testing workflow into:

- `legacy_concept_testing_backup/`

Backup scope should include at least:

- `advanced_testing.py`
- `concept_testing.py`
- `dingtalk_bot.py`
- `html_report_renderer.py`
- `langgraph_flows.py`
- `langgraph_nodes.py`
- `langgraph_state.py`
- `run_single_concept_report.py`
- `task_session_manager.py`
- `tests/test_advanced_testing.py`
- `tests/test_concept_testing.py`
- `tests/test_dingtalk_workflow.py`

The active entrypoints should remain stable where practical, especially the DingTalk bot entrypoint.

## Testing Strategy

### Domain Tests

Verify:

- multi mode returns 8 mother responses plus one research summary
- single mode returns one selected mother response plus one research summary
- question type routing works for the four supported categories
- the summary always includes the seven fixed sections

### Session and Workflow Tests

Verify:

- natural-language input can infer question type and mode when obvious
- semi-structured input overrides inference
- single mode without persona triggers a follow-up
- follow-up messages reuse the same session
- completed runs still return DingTalk summary, JSON path, HTML path, and optional public URL

### Renderer Tests

Verify:

- HTML contains consumer voice and research summary sections
- HTML shows multi-mode persona cards and single-mode detail cards
- old quantitative report sections do not appear in the new report

## Non-Goals

- redefining the 8 mother personas
- preserving the old concept-testing report schema
- keeping the old quantitative recommendation flow active in the primary path
