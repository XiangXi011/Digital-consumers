# DingTalk Bot And HTML Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a DingTalk-oriented workflow that collects product information via chat, supports partial-run confirmation, and generates a polished HTML report plus a short completion summary.

**Architecture:** Add a file-backed session manager, a DingTalk workflow service, and a dedicated HTML renderer. Keep analysis delegated to the existing concept-testing stack and keep local output artifacts in the workspace.

**Tech Stack:** Python, unittest, JSON, HTML, local filesystem storage

---

### Task 1: Add Failing Tests For Workflow And HTML Rendering

**Files:**
- Create: `tests/test_dingtalk_workflow.py`
- Test: `tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Add tests that verify:
- first contact returns the full information checklist
- partial information updates the session and triggers missing-field follow-up
- explicit partial-run confirmation starts analysis
- completing an analysis returns summary plus HTML report metadata
- rendered HTML contains the key visual sections

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: FAIL because the new workflow modules do not exist yet.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 2: Implement Session Management

**Files:**
- Create: `task_session_manager.py`

**Step 1: Write minimal implementation**

Implement:
- task session data structure
- file-backed save/load
- message field extraction
- missing-field calculation
- run-authorization state handling

**Step 2: Run tests**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: some tests still fail, but session behavior should move forward.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 3: Implement HTML Rendering

**Files:**
- Create: `html_report_renderer.py`

**Step 1: Write minimal implementation**

Render a polished HTML report with:
- hero header
- KPI cards
- segment ranking
- reasons / barriers cards
- consumer quotes
- missing-information appendix

**Step 2: Run tests**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: HTML-related tests pass.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 4: Implement DingTalk Workflow Service

**Files:**
- Create: `dingtalk_bot.py`

**Step 1: Write minimal implementation**

Implement:
- normalized message handler
- checklist response
- missing-field follow-up
- partial-run confirmation logic
- analysis kickoff
- completion packaging with HTML output metadata

**Step 2: Run tests**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: PASS.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 5: Add A Runnable Demo And Verify

**Files:**
- Create: `run_dingtalk_demo.py`

**Step 1: Write minimal implementation**

Create a simple scripted conversation that:
- starts a task
- provides partial info
- confirms partial execution
- generates an HTML report

**Step 2: Run full verification**

Run:
- `python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing tests.test_dingtalk_workflow -v`
- `python .\\run_dingtalk_demo.py`

**Step 3: Summarize**

Report:
- workflow behavior
- where HTML files are stored
- what still needs real DingTalk callback binding

**Step 4: Commit**

Skip commit because this workspace is not a git repository.
