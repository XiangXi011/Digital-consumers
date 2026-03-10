# Advanced Testing And AI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OpenAI-compatible AI adapters plus A/B testing, price ladder testing, packaging vision review, and optional LLM-enhanced report language.

**Architecture:** Introduce a dedicated `ai_clients.py` module for OpenAI-compatible text and vision access, and an `advanced_testing.py` module that extends the current concept-testing workflow into A/B, pricing, and packaging analysis. Preserve rule-based scoring while using LLMs only for expression and visual summarization.

**Tech Stack:** Python, unittest, OpenAI-compatible HTTP client via `openai`, PIL for local image handling, JSON, Markdown

---

### Task 1: Add Failing Tests for Advanced Capabilities

**Files:**
- Create: `tests/test_advanced_testing.py`
- Test: `tests/test_advanced_testing.py`

**Step 1: Write the failing test**

Add tests that verify:
- AI client fallback mode when no API config is set
- concept runner can optionally use an injected text generator
- A/B comparison returns both variants, a winner, and segment deltas
- price ladder returns one result per price and a recommended price zone
- packaging review accepts a local image path and returns structured packaging signals

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_advanced_testing -v`

Expected: FAIL because the new advanced modules do not exist yet.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 2: Implement OpenAI-Compatible AI Adapters

**Files:**
- Create: `ai_clients.py`

**Step 1: Write minimal implementation**

Implement:
- configuration loading from environment
- a text generation client wrapper
- a vision analysis client wrapper
- local fallback behavior when configuration is missing

**Step 2: Run tests**

Run: `python -m unittest tests.test_advanced_testing -v`

Expected: some tests still fail, but AI adapter tests should pass or move forward.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 3: Implement Advanced Testing Flows

**Files:**
- Create: `advanced_testing.py`
- Modify: `concept_testing.py` only where minimal extension hooks are needed

**Step 1: Write minimal implementation**

Implement:
- A/B report workflow
- price ladder workflow
- packaging image review workflow
- optional LLM-enhanced text hooks

**Step 2: Run tests**

Run: `python -m unittest tests.test_advanced_testing -v`

Expected: PASS.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 4: Add Runnable Example Entry Points

**Files:**
- Create: `run_ab_test_report.py`
- Create: `run_price_ladder_report.py`
- Create: `run_packaging_review.py`

**Step 1: Write minimal implementation**

Create thin scripts that:
- build sample inputs
- invoke the advanced workflows
- write JSON and Markdown outputs

**Step 2: Smoke test**

Run all three scripts and confirm output files are created.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 5: Final Verification

**Files:**
- Review only: new modules and output files

**Step 1: Run verification**

Run:
- `python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing -v`
- `python .\\run_single_concept_report.py`
- `python .\\run_ab_test_report.py`
- `python .\\run_price_ladder_report.py`
- `python .\\run_packaging_review.py`

**Step 2: Summarize**

Report:
- what advanced boundaries were added
- how fallback mode behaves
- what still requires live API configuration for best results

**Step 3: Commit**

Skip commit because this workspace is not a git repository.
