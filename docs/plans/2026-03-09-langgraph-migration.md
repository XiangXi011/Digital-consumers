# LangGraph Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the hand-written orchestration flow with LangGraph for conversation handling and analysis execution while preserving the current market-testing outputs.

**Architecture:** A LangGraph main graph will manage DingTalk-style interaction flow and task execution routing. A LangGraph analysis subgraph will manage deterministic concept testing steps and reuse the current persona engine, scoring logic, and report renderer.

**Tech Stack:** Python, LangGraph, dataclasses/typed state, existing legacy simulation engine, unittest

---

### Task 1: Add failing LangGraph behavior tests

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_dingtalk_workflow.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_concept_testing.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_advanced_testing.py`

**Step 1: Write the failing tests**

Add assertions that the public entrypoints are backed by graph-style execution behavior and still return the same business outputs.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_concept_testing tests.test_advanced_testing -v`

Expected: FAIL because the LangGraph-specific APIs and integration points do not exist yet.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 2: Add shared LangGraph state and node primitives

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\langgraph_state.py`
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\langgraph_nodes.py`

**Step 1: Write the failing test**

Use the failures from Task 1 as the driver.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_concept_testing -v`

Expected: FAIL because graph state/nodes are missing.

**Step 3: Write minimal implementation**

Add the typed state helpers and the node functions needed by the main graph and analysis subgraph.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_concept_testing -v`

Expected: partial progress, some tests still failing until graph assembly exists.

### Task 3: Assemble the LangGraph main graph and analysis subgraph

**Files:**
- Create: `C:\Users\05537\Desktop\agent\市场部agent teams\langgraph_flows.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\concept_testing.py`

**Step 1: Write the failing test**

Use single concept report tests as the driver for graph-backed execution.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_concept_testing -v`

Expected: FAIL because the graph-backed runner does not yet exist.

**Step 3: Write minimal implementation**

Create the main `StateGraph` and analysis subgraph, then adapt `ConceptTestRunner` to invoke the analysis graph while preserving report shape.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_concept_testing -v`

Expected: PASS

### Task 4: Switch DingTalk workflow to LangGraph

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\dingtalk_bot.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\run_dingtalk_demo.py`

**Step 1: Write the failing test**

Use the DingTalk workflow tests as the driver.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: FAIL until the main graph is wired into the public workflow API.

**Step 3: Write minimal implementation**

Replace the hand-written workflow routing with the LangGraph main graph while preserving the public response contract.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: PASS

### Task 5: Switch advanced testing flows to graph-backed execution

**Files:**
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\advanced_testing.py`
- Modify: `C:\Users\05537\Desktop\agent\市场部agent teams\tests\test_advanced_testing.py`

**Step 1: Write the failing test**

Use advanced-testing structure tests as the driver.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_advanced_testing -v`

Expected: FAIL until advanced flows call into the graph-backed concept analysis.

**Step 3: Write minimal implementation**

Refactor advanced testing helpers to use the graph-backed single concept execution path and preserve existing output formats.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_advanced_testing -v`

Expected: PASS

### Task 6: Full verification

**Files:**
- Verify only

**Step 1: Run full test suite**

Run: `python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing tests.test_dingtalk_workflow -v`

Expected: PASS

**Step 2: Run demo workflow**

Run: `python .\run_dingtalk_demo.py`

Expected: demo completes and writes HTML/JSON outputs

**Step 3: Verify live LLM config still works**

Run a minimal text and image probe through `ai_clients.py`

Expected: live text and live vision succeed with the configured SiliconFlow model
