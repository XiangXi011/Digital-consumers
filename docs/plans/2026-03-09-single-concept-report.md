# Single Concept Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable single-concept testing workflow that runs the 200 personas and outputs a business-readable full report.

**Architecture:** Add a new `concept_testing.py` module that dynamically loads the existing persona engine, maps one concept input into a `Product`, runs batch evaluation plus discussion plus deep dive, and synthesizes both JSON and Markdown outputs. Keep the new workflow separate from the legacy orchestrator file so future A/B and pricing flows can extend cleanly.

**Tech Stack:** Python, unittest, JSON, Markdown, dynamic module loading via `importlib`

---

### Task 1: Add Failing Tests for the New Workflow

**Files:**
- Create: `tests/test_concept_testing.py`
- Test: `tests/test_concept_testing.py`

**Step 1: Write the failing test**

Add tests that:
- load the new concept-testing module by path
- create a standard single-concept input
- assert it maps correctly into the legacy `Product`
- assert the runner returns the required report sections
- assert discussion participants cover all 8 mother segments when full data is available
- assert deep-dive selection returns `2 high + 2 hesitant + 2 rejecting`
- assert Markdown rendering includes the key business report headings

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_concept_testing -v`

Expected: FAIL because `concept_testing.py` does not exist yet.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 2: Implement the Concept Input and Runner

**Files:**
- Create: `concept_testing.py`
- Modify: `digital_consumer_agents(1).py` only if a minimal compatibility fix becomes necessary

**Step 1: Write minimal implementation**

Implement:
- a `ConceptTestInput` dataclass
- a `ConceptTestRunner` class
- dynamic loading for `digital_consumer_agents(1).py`
- concept-to-product mapping
- full batch evaluation
- representative discussion selection
- deep-dive bucket selection
- report synthesis into the approved section structure
- Markdown rendering

**Step 2: Run tests to verify behavior**

Run: `python -m unittest tests.test_concept_testing -v`

Expected: PASS.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 3: Add a Runnable Entry Point

**Files:**
- Create: `run_single_concept_report.py`

**Step 1: Write the failing test**

Skip direct CLI testing in version one. Cover the underlying behavior via unit tests and keep the CLI thin.

**Step 2: Write minimal implementation**

Add a small script that:
- builds a sample concept input
- runs the new workflow
- writes JSON and Markdown outputs to disk

**Step 3: Smoke test**

Run: `python .\\run_single_concept_report.py`

Expected: two report files written successfully.

**Step 4: Commit**

Skip commit because this workspace is not a git repository.

### Task 4: Verify with Existing Persona Data

**Files:**
- Modify: generated output files only

**Step 1: Run full verification**

Run:
- `python -m unittest tests.test_concept_testing -v`
- `python -m unittest tests.test_generate_personas_constraints -v`
- `python .\\run_single_concept_report.py`

**Step 2: Inspect outputs**

Confirm:
- the workflow loads all 200 personas
- report sections are complete
- segment opportunity and voice sections are populated
- no empty discussion/deep-dive blocks are produced

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 5: Final Sanity Review

**Files:**
- Review only: `concept_testing.py`
- Review only: `run_single_concept_report.py`
- Review only: generated report artifacts

**Step 1: Review residual issues**

Check for:
- unnecessary coupling to the legacy engine
- unstable selection heuristics
- missing fields in the Markdown report

**Step 2: Summarize final state**

Report:
- what was added
- how to run it
- what version one still does not do

**Step 3: Commit**

Skip commit because this workspace is not a git repository.
