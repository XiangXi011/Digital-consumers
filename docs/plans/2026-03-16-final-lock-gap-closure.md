# Final Lock Gap Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the DingTalk market-research workflow back into alignment with the 2.5.1 Final Lock contract and restore the broken test suite.

**Architecture:** Collapse the execution path around a single typed `BusinessBrief` and a typed `ReadinessGate` decision, then thread that contract through planning, persona dispatch, synthesis, persistence, and reporting. Wire the runtime guards at the stream entrypoint, restrict RA to structured evidence only, and enforce privacy/reporting constraints in code and tests.

**Tech Stack:** Python, Pydantic, LangGraph, pytest, DingTalk stream adapter

---

### Task 1: Lock Failing Contract Tests

**Files:**
- Modify: `tests/test_qualitative_research.py`
- Modify: `tests/test_dingtalk_workflow.py`
- Modify: `tests/test_qualitative_regression.py`
- Create: `tests/test_final_lock_contract.py`

**Step 1: Write the failing tests**

- Add assertions that downstream planning and dispatch use `BusinessBrief`-derived payload, not raw session fields.
- Add assertions that readiness is decided by a typed readiness result before planner dispatch.
- Add assertions that RA prompt does not include raw `mom_outputs`.
- Add assertions that final HTML contains the required contract sections and persona card fields.
- Add assertions that stream ingress applies dedup and ordering guards.

**Step 2: Run the focused tests to verify they fail**

Run: `python -m pytest tests/test_qualitative_research.py tests/test_dingtalk_workflow.py tests/test_qualitative_regression.py tests/test_final_lock_contract.py -q`

**Step 3: Confirm failure reasons**

- Expect failures tied to `total_agents == 0`, missing contract fields, and missing runtime guard integration.

### Task 2: Make `BusinessBrief` the Only Downstream Business Context

**Files:**
- Modify: `business_brief.py`
- Modify: `langgraph_nodes.py`
- Modify: `langgraph_state.py`
- Modify: `task_session_manager.py`
- Test: `tests/test_final_lock_contract.py`

**Step 1: Write the failing test**

- Assert that `start_analysis` and task execution consume a serialized `BusinessBrief` snapshot, not `session.fields`.

**Step 2: Run the single test to verify it fails**

Run: `python -m pytest tests/test_final_lock_contract.py::test_downstream_uses_business_brief_only -q`

**Step 3: Write minimal implementation**

- Add a `BusinessBrief` snapshot onto `TaskSession`.
- Make `build_business_brief` persist that snapshot.
- Replace `build_research_input_payload(session)` usage with `build_research_input_payload_from_brief(brief)` or equivalent.
- Ensure planner, personas, and report payloads all derive from the brief snapshot.

**Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_final_lock_contract.py::test_downstream_uses_business_brief_only -q`

### Task 3: Make `ReadinessGate` the Single Readiness Judge

**Files:**
- Modify: `langgraph_nodes.py`
- Modify: `business_brief.py`
- Modify: `qualitative_research.py`
- Test: `tests/test_final_lock_contract.py`
- Test: `tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

- Assert that missing required brief fields are blocked by `ReadinessGate` before planner dispatch.
- Assert that planner can no longer veto readiness with `ready_to_dispatch=false`; planner may only shape dispatch scope/questions.

**Step 2: Run the focused tests to verify they fail**

Run: `python -m pytest tests/test_final_lock_contract.py::test_readiness_gate_is_single_decider tests/test_dingtalk_workflow.py::DingTalkWorkflowTest::test_planner_blocked_request_returns_clarification_message -q`

**Step 3: Write minimal implementation**

- Introduce a typed readiness decision object or dict with `recommended_state`, `blocking_reasons`, and `authorization_needed`.
- Put business completeness rules into `ReadinessGate`.
- Remove planner-owned readiness semantics from the workflow path.

**Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_final_lock_contract.py::test_readiness_gate_is_single_decider tests/test_dingtalk_workflow.py::DingTalkWorkflowTest::test_planner_blocked_request_returns_clarification_message -q`

### Task 4: Stop Swallowing Persona Failures and Restrict RA to Evidence Only

**Files:**
- Modify: `qualitative_research.py`
- Modify: `evidence_models.py`
- Test: `tests/test_qualitative_research.py`
- Test: `tests/test_ra_evidence_assembly.py`
- Test: `tests/test_final_lock_contract.py`

**Step 1: Write the failing tests**

- Assert that a persona mismatch raises instead of silently disappearing.
- Assert that successful persona runs produce the expected agent count.
- Assert that RA prompt contains structured evidence groups but not raw persona output dumps.

**Step 2: Run the focused tests to verify they fail**

Run: `python -m pytest tests/test_qualitative_research.py tests/test_ra_evidence_assembly.py tests/test_final_lock_contract.py::test_ra_prompt_excludes_raw_persona_outputs -q`

**Step 3: Write minimal implementation**

- Replace the broken async/coroutine handling with task objects that preserve results and exceptions.
- Fail hard when contract-required persona output is missing in non-partial paths.
- Remove raw `mom_outputs` from the RA prompt; pass only `RAInput`, assumptions, and evidence groups.

**Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_qualitative_research.py tests/test_ra_evidence_assembly.py tests/test_final_lock_contract.py::test_ra_prompt_excludes_raw_persona_outputs -q`

### Task 5: Wire Runtime Guards at Stream Ingress

**Files:**
- Modify: `dingtalk_stream_service.py`
- Modify: `dingtalk_bot.py`
- Modify: `redis_infra.py`
- Test: `tests/test_dingtalk_stream_service.py`
- Test: `tests/test_final_lock_contract.py`

**Step 1: Write the failing tests**

- Assert duplicate messages are accepted with no workflow execution.
- Assert stale events are ignored.
- Assert dispatch-phase follow-up messages enter `SuspendQueue`.

**Step 2: Run the focused tests to verify they fail**

Run: `python -m pytest tests/test_dingtalk_stream_service.py tests/test_final_lock_contract.py::test_runtime_guards_are_applied_at_ingress -q`

**Step 3: Write minimal implementation**

- Instantiate guard objects from the store abstraction.
- Apply dedup and ordering checks before `workflow.handle_message`.
- Route dispatch-phase user supplements into `SuspendQueue`.

**Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_dingtalk_stream_service.py tests/test_final_lock_contract.py::test_runtime_guards_are_applied_at_ingress -q`

### Task 6: Enforce Reporting Contract and Privacy Rules

**Files:**
- Modify: `html_report_renderer.py`
- Modify: `privacy_utils.py`
- Modify: `langgraph_nodes.py`
- Modify: `task_session_manager.py`
- Test: `tests/test_qualitative_regression.py`
- Test: `tests/test_final_lock_contract.py`

**Step 1: Write the failing tests**

- Assert the HTML contains the nine required sections.
- Assert persona cards contain `purchase_intent`, `purchase_score`, chart data, `voice_line`, and `what_would_change_my_mind`.
- Assert stored session/report payloads hash user/group identifiers and sanitize user-facing HTML.

**Step 2: Run the focused tests to verify they fail**

Run: `python -m pytest tests/test_qualitative_regression.py tests/test_final_lock_contract.py::test_html_and_privacy_contract -q`

**Step 3: Write minimal implementation**

- Reshape the renderer around the Final Lock HTML contract.
- Persist and render backend evaluation fields.
- Call `sanitize_report()` before writing/publishing HTML.
- Hash at-rest identifiers in session/report persistence paths or serialized payloads.

**Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_qualitative_regression.py tests/test_final_lock_contract.py::test_html_and_privacy_contract -q`

### Task 7: Full Verification

**Files:**
- Modify: none unless a regression appears
- Test: `tests/`

**Step 1: Run targeted suites**

Run: `python -m pytest tests/test_qualitative_research.py tests/test_dingtalk_workflow.py tests/test_dingtalk_stream_service.py tests/test_qualitative_regression.py tests/test_final_lock_contract.py -q`

**Step 2: Run full suite**

Run: `python -m pytest tests -q`

**Step 3: Record residual risks**

- Note any remaining gaps around replay snapshots, retention cleanup jobs, or observability metrics if they are still not fully enforced.

**Step 4: Commit**

```bash
git add business_brief.py langgraph_nodes.py langgraph_state.py task_session_manager.py qualitative_research.py dingtalk_stream_service.py dingtalk_bot.py html_report_renderer.py privacy_utils.py tests docs/plans/2026-03-16-final-lock-gap-closure.md
git commit -m "fix: close final lock contract gaps"
```
