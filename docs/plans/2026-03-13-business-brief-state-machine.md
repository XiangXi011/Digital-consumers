# Business Brief State Machine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild DingTalk intake around `BusinessBrief`, `ReadinessGate`, `UserMessagePresenter`, and recoverable workflow states so business users can start research naturally without seeing internal workflow details.

**Architecture:** Add dedicated modules for brief normalization, readiness evaluation, presenter translation, and recovery payloads; refit the existing workflow graph so all execution decisions pass through `ReadinessGate`, planner consumes only `BusinessBrief`, and user-facing responses are rendered through `UserMessagePresenter`.

**Tech Stack:** Python, dataclasses, LangGraph workflow nodes, unittest

---

### Task 1: Add Business Brief Domain Models

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\business_brief.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\langgraph_state.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_business_brief.py`

**Step 1: Write the failing test**

Add tests for:
- default `task_type`/`effective_task_type`
- structured fact storage
- assumption persistence
- degrade history persistence

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_business_brief -v`

Expected: FAIL because `business_brief.py` and dataclasses do not exist.

**Step 3: Write minimal implementation**

Create:
- `StructuredFacts`
- `BusinessBrief`
- helper functions to serialize/deserialize brief state

Update `langgraph_state.py` with `business_brief`, `readiness_decision`, and `recovery_payload` fields.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_business_brief -v`

Expected: PASS

### Task 2: Add Natural-Language Intake Normalizer

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\business_brief_parser.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\task_session_manager.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_business_brief_parser.py`

**Step 1: Write the failing test**

Cover:
- concept + selling points => `concept_test`
- explicit copy line => `copy_feedback`
- two versions => `ab_test`
- price acceptance => `price_test`
- extract brand, product name, spec, flavor, age, channel, price, selling points, scenes
- authorization phrases normalize to `execution_authorized = true`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_business_brief_parser -v`

Expected: FAIL because parser logic does not exist.

**Step 3: Write minimal implementation**

Implement parser helpers that:
- infer task type in fixed priority order
- extract structured facts from natural language
- capture copy candidates, price context, and comparison context
- normalize execution authorization phrases
- build/update `BusinessBrief` from session messages

Keep the first version deterministic and rule-based.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_business_brief_parser -v`

Expected: PASS

### Task 3: Add ReadinessGate

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\readiness_gate.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\business_brief_parser.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_readiness_gate.py`

**Step 1: Write the failing test**

Cover:
- minimum field sets per task type
- `copy_feedback -> concept_test`
- `ab_test -> copy_feedback -> concept_test`
- `price_test -> concept_test`
- assumptions added when execution is allowed under incomplete detail
- no authorization => `awaiting_authorization`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_readiness_gate -v`

Expected: FAIL because gate logic does not exist.

**Step 3: Write minimal implementation**

Implement:
- `ReadinessDecision`
- minimum field checks
- downgrade chain evaluation
- assumption generation
- user-facing awaiting status selection

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_readiness_gate -v`

Expected: PASS

### Task 4: Add UserMessagePresenter

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\user_message_presenter.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_user_message_presenter.py`

**Step 1: Write the failing test**

Cover:
- task label translation
- status translation
- no internal terms leak
- explicit downgrade explanation
- explicit assumption explanation
- four-part recovery message

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_user_message_presenter -v`

Expected: FAIL because presenter does not exist.

**Step 3: Write minimal implementation**

Implement presenter methods for:
- intake/readiness
- dispatch started
- completion summary
- recovery payload rendering

Ensure forbidden technical terms are not emitted.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_user_message_presenter -v`

Expected: PASS

### Task 5: Add Recovery Payloads

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\recovery.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_recovery.py`

**Step 1: Write the failing test**

Cover:
- planner failure payload
- mother-agent failure payload
- synthesizer failure payload
- preserved information list
- suggested reply generation

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_recovery -v`

Expected: FAIL because recovery helpers do not exist.

**Step 3: Write minimal implementation**

Implement:
- `RecoveryPayload`
- helper builders for planner, dispatch, and synthesis failures
- preserved-information summary from `BusinessBrief`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_recovery -v`

Expected: PASS

### Task 6: Refactor Session Storage Around BusinessBrief

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\task_session_manager.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_task_session_manager.py`

**Step 1: Write the failing test**

Cover:
- session stores serialized `BusinessBrief`
- session reload preserves assumptions and degrade history
- legacy fields are no longer required for readiness

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_task_session_manager -v`

Expected: FAIL against current field-centric implementation.

**Step 3: Write minimal implementation**

Refactor session state to store:
- `business_brief`
- `readiness_decision`
- `recovery_payload`

Keep any legacy fields only as migration compatibility, not as source of truth.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_task_session_manager -v`

Expected: PASS

### Task 7: Refactor Workflow Nodes to Six-Stage Flow

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\langgraph_nodes.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\langgraph_flows.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\dingtalk_bot.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Add/update workflow tests for:
- `Intake -> Normalize -> ReadinessGate`
- ready but unauthorized => follow-up authorization message
- authorized + downgraded => running with explicit downgrade explanation
- gate-only control over readiness
- planner failure => recovery response

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: FAIL against current planner-first but field-centric flow.

**Step 3: Write minimal implementation**

Refactor nodes to:
- build/update `BusinessBrief`
- evaluate `ReadinessGate`
- route to authorization wait, clarification wait, planner, or recovery
- render all messages through `UserMessagePresenter`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: PASS

### Task 8: Refactor Planner and Runner Inputs

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\qualitative_research.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_qualitative_research.py`

**Step 1: Write the failing test**

Cover:
- planner prompt includes brief assumptions
- planner prompt reads business brief, not legacy task fields
- report preserves assumptions, effective task type, degrade history

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: FAIL against current input contract.

**Step 3: Write minimal implementation**

Update:
- planner input model to accept `BusinessBrief`
- runner output to include execution boundary fields
- dispatch prompts to carry assumptions and effective task type

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: PASS

### Task 9: Refactor DingTalk Stream Recovery Path

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\dingtalk_stream_service.py`
- Test: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_dingtalk_stream_service.py`

**Step 1: Write the failing test**

Cover:
- recovery payload text returned for planner failure
- recovery payload text returned for agent failure
- recovery payload text returned for synthesizer failure
- no generic retry-only reply in these cases

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_stream_service -v`

Expected: FAIL against current generic incomplete-result path.

**Step 3: Write minimal implementation**

Update stream handler to forward presenter-rendered recovery messages from workflow/bot responses and preserve task/session state.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_stream_service -v`

Expected: PASS

### Task 10: Add End-to-End Intake and State-Flow Regression Tests

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_dingtalk_workflow.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_qualitative_regression.py`

**Step 1: Write the failing test**

Add full-path cases for:
- concept default route
- copy route
- A/B route
- price route
- downgrade with explicit explanation
- assumption execution with visible assumptions
- recoverable planner failure
- recoverable agent failure

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_qualitative_regression -v`

Expected: FAIL until all refactors are wired together.

**Step 3: Write minimal implementation**

Adjust regression fixtures and expected outputs to reflect:
- `BusinessBrief`
- `ReadinessDecision`
- `RecoveryPayload`
- presenter-rendered user messages

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_qualitative_regression -v`

Expected: PASS

### Task 11: Run Full Verification

**Files:**
- No code changes required

**Step 1: Run targeted suite**

Run:

```powershell
python -m unittest tests.test_business_brief tests.test_business_brief_parser tests.test_readiness_gate tests.test_user_message_presenter tests.test_recovery tests.test_task_session_manager tests.test_qualitative_research tests.test_dingtalk_workflow tests.test_dingtalk_stream_service tests.test_qualitative_regression -v
```

Expected: all pass

**Step 2: Run syntax verification**

Run:

```powershell
python -m py_compile business_brief.py business_brief_parser.py readiness_gate.py user_message_presenter.py recovery.py task_session_manager.py qualitative_research.py langgraph_nodes.py langgraph_flows.py dingtalk_bot.py dingtalk_stream_service.py
```

Expected: no output, exit code 0

**Step 3: Inspect a sample report**

Verify report now contains:
- `business_brief`
- `effective_task_type`
- `assumptions`
- `degrade_history`
- `research_plan`
- `structured_recommendation`

### Task 12: Manual Smoke in Current DingTalk Path

**Files:**
- No code changes required

**Step 1: Run local smoke**

Trigger sample conversations covering:
- concept input
- explicit copy input
- A/B input
- price input
- recovery flow

**Step 2: Verify DingTalk-facing copy**

Confirm:
- no internal terms leak
- downgrade is explicit
- recovery output is four-part and actionable

**Step 3: Record residual risk**

If runtime remains blocked by Python 3.14 preflight, document that as environment risk rather than application logic failure.
