# LangSmith Selective Tracing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional LangSmith tracing for LLM, image, and OCR calls without tracing the DingTalk or LangGraph workflow.

**Architecture:** Keep all tracing inside `ai_clients.py`. Public AI client methods become thin trace boundaries that call existing private behavior. When LangSmith is missing or disabled, wrappers become no-ops and behavior remains unchanged.

**Tech Stack:** Python, unittest, LangSmith, OpenAI-compatible API

---

### Task 1: Add failing tests for LangSmith config and trace-safe execution

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_advanced_testing.py`

**Step 1: Write the failing test**

Add focused tests for:

```python
def test_langsmith_config_can_load_workspace_dotenv():
    ...

def test_langsmith_tracing_stays_disabled_without_api_key():
    ...

def test_traced_quote_and_validation_calls_keep_return_shape():
    ...

def test_remote_ocr_path_works_with_tracing_enabled():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_advanced_testing.AdvancedTestingTest.test_langsmith_config_can_load_workspace_dotenv tests.test_advanced_testing.AdvancedTestingTest.test_langsmith_tracing_stays_disabled_without_api_key tests.test_advanced_testing.AdvancedTestingTest.test_traced_quote_and_validation_calls_keep_return_shape tests.test_advanced_testing.AdvancedTestingTest.test_remote_ocr_path_works_with_tracing_enabled -v
```

Expected: FAIL because LangSmith config and wrappers do not exist yet.

**Step 3: Write minimal implementation**

Do not implement here.

**Step 4: Run test to verify it passes**

Run the same command after Task 2.

### Task 2: Implement optional LangSmith config and safe tracing wrappers

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/ai_clients.py`

**Step 1: Use the failing tests from Task 1**

No new tests here.

**Step 2: Write minimal implementation**

Add:

- `LangSmithConfig`
- a truthy flag parser
- optional `langsmith.traceable` import
- a safe wrapper helper
- traced boundaries for:
  - `generate_text`
  - `analyze_image`
  - `_extract_ocr_text_via_remote`
  - `generate_consumer_quote`
  - `validate_consumer_quote`

Preserve all existing return shapes and fallback behavior.

**Step 3: Run targeted tests**

Run:

```powershell
python -m unittest tests.test_advanced_testing.AdvancedTestingTest.test_langsmith_config_can_load_workspace_dotenv tests.test_advanced_testing.AdvancedTestingTest.test_langsmith_tracing_stays_disabled_without_api_key tests.test_advanced_testing.AdvancedTestingTest.test_traced_quote_and_validation_calls_keep_return_shape tests.test_advanced_testing.AdvancedTestingTest.test_remote_ocr_path_works_with_tracing_enabled -v
```

Expected: PASS

### Task 3: Install dependency and wire local environment

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/.env`
- Create if needed: `C:/Users/05537/Desktop/agent/市场部agent teams/requirements.txt`

**Step 1: Install dependency**

Run:

```powershell
python -m pip install -U langsmith
```

Expected: install succeeds.

**Step 2: Update local env**

Ensure `.env` contains:

- `LANGSMITH_TRACING=true`
- `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`
- `LANGSMITH_API_KEY=...`
- `LANGSMITH_PROJECT=数字消费者`

**Step 3: Track dependency**

If the repo has no dependency manifest, add a minimal `requirements.txt` entry for `langsmith`.

### Task 4: Run regression and live smoke verification

**Files:**
- No code changes required

**Step 1: Run focused AI tests**

```powershell
python -m unittest tests.test_advanced_testing -v
```

Expected: PASS

**Step 2: Run broader regression**

```powershell
python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 3: Run live LangSmith smoke**

Execute one minimal real text generation call using workspace config and confirm it returns without exception.

**Step 4: If needed, restart DingTalk bot**

If the running bot process uses an older environment snapshot, restart it so the new tracing config applies.
