# LangSmith Selective Tracing Design

**Date:** 2026-03-10

## Goal

Integrate LangSmith into the digital consumer platform, but only for model-facing calls:

- text LLM calls
- image understanding calls
- OCR calls

The DingTalk workflow, LangGraph orchestration, HTML rendering, and report publishing must remain untraced.

## Scope

Trace only these AI client methods:

- `OpenAICompatibleClient.generate_text`
- `OpenAICompatibleClient.analyze_image`
- `OpenAICompatibleClient._extract_ocr_text_via_remote`
- `OpenAICompatibleClient.generate_consumer_quote`
- `OpenAICompatibleClient.validate_consumer_quote`

Do not add tracing to:

- `dingtalk_bot.py`
- `langgraph_nodes.py`
- `langgraph_flows.py`
- `dingtalk_stream_service.py`
- `html_report_renderer.py`

## Design Principles

1. Tracing must be optional.
2. If LangSmith is missing or disabled, the system must behave exactly as before.
3. Instrumentation failures must never break report generation.
4. Only model-adjacent spans should appear in LangSmith.
5. Existing fallback behavior must remain unchanged.

## Configuration

Read LangSmith settings from `.env` or environment variables:

- `LANGSMITH_TRACING`
- `LANGSMITH_ENDPOINT`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`

Tracing is enabled only when:

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY` is non-empty

If tracing is disabled, all wrappers become no-ops.

## Implementation Approach

Add a small tracing helper layer in `ai_clients.py`:

- a config loader for LangSmith values
- a boolean `is_enabled` gate
- a safe trace decorator factory
- a wrapper runner that catches tracing setup problems and falls back to direct execution

Instead of decorating the methods directly at import time, wrap the internal execution path. This avoids brittle behavior when LangSmith is absent or env vars are incomplete.

Suggested structure:

- `_load_workspace_dotenv(...)`
- `LangSmithConfig.from_env(...)`
- `_is_truthy_flag(...)`
- `_run_with_optional_trace(...)`

Then split each traced method into:

- public method: trace boundary
- private method: real implementation

Example pattern:

```python
def generate_text(...):
    return self._run_with_optional_trace(
        "ai.generate_text",
        "llm",
        lambda: self._generate_text_impl(...),
        metadata={...},
    )
```

## Run Types

Use LangSmith run types conservatively:

- `run_type="llm"` for:
  - `generate_text`
  - `generate_consumer_quote`
  - `validate_consumer_quote`
- `run_type="tool"` for:
  - `analyze_image`
  - `_extract_ocr_text_via_remote`

This keeps traces readable and avoids over-modeling OCR as an LLM call.

## Test Strategy

Add test coverage for:

1. LangSmith config loads from `.env`
2. tracing gate stays off when config is incomplete
3. traced methods still return existing shapes when tracing is off
4. traced methods still return existing shapes when tracing is on
5. quote generation / validation behavior stays unchanged under tracing
6. OCR remote path still works under tracing

Also run one live connectivity smoke test after implementation:

- import client with real workspace `.env`
- call one minimal `generate_text`
- confirm no exception

If practical, also check the LangSmith project receives the trace. This is a manual validation step, not a unit test.

## Risks

- import-time LangSmith failures breaking the AI client
- tracing wrappers accidentally tracing the whole workflow
- leaking secrets through debug logging
- changing fallback behavior in quote or OCR paths

## Non-Goals

- full LangGraph tracing
- DingTalk message tracing
- report-level tracing
- Vercel publish tracing
