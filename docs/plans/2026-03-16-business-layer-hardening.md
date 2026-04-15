# Business Layer Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore business-level correctness for task-type preservation, follow-up arbitration, and explicit single-persona execution.

**Architecture:** We will tighten backend business contracts instead of adding more prompt guidance. Intake will collect the missing business fields, `BusinessBrief` will preserve task semantics end-to-end, and workflow ingress will apply rule-first follow-up arbitration before any new message mutates session state.

**Tech Stack:** Python, LangGraph workflow nodes, Pydantic business contracts, unittest/pytest regression tests

---

### Task 1: Add regression tests for business task-type preservation

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_final_lock_contract.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Add tests that prove:
- `purchase_decision` survives `BusinessBrief -> research_input` projection
- `ab_test` and `price_test` can be built from session fields without manual payload injection

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_final_lock_contract.py tests/test_qualitative_research.py -q`

Expected: FAIL on missing mappings or dropped task types.

**Step 3: Write minimal implementation**

Update intake aliases, field parsing, and `BusinessBrief` mapping logic.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_final_lock_contract.py tests/test_qualitative_research.py -q`

Expected: PASS for the new task-type tests.

### Task 2: Add regression tests for follow-up arbitration at workflow ingress

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_followup_rule_override.py`

**Step 1: Write the failing test**

Add a workflow test showing that:
- after one completed task, an unrelated next message clears prior business state
- previous `follow_up_context` does not leak into the new task

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dingtalk_workflow.py tests/test_followup_rule_override.py -q`

Expected: FAIL because the current workflow bypasses adjudication and reuses prior session context.

**Step 3: Write minimal implementation**

Wire follow-up adjudication into workflow ingress and add session reset-for-new-task behavior.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dingtalk_workflow.py tests/test_followup_rule_override.py -q`

Expected: PASS.

### Task 3: Enforce explicit single-persona execution

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Add a test where the user requests `single` mode with `persona_id`, but the planner returns multi-persona output.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_qualitative_research.py -q`

Expected: FAIL because the planner output is currently trusted.

**Step 3: Write minimal implementation**

Normalize or reject planner scope drift when the user explicitly requested a single persona.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_qualitative_research.py -q`

Expected: PASS.

### Task 4: Full verification

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/business_brief.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`

**Step 1: Run focused regression commands**

Run:
- `python -m pytest tests/test_final_lock_contract.py tests/test_qualitative_research.py tests/test_dingtalk_workflow.py tests/test_followup_rule_override.py -q`

Expected: all pass.

**Step 2: Run full verification**

Run:
- `python -m pytest tests -q`

Expected: full suite passes with no new failures.
