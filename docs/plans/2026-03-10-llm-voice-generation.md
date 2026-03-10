# LLM Voice Generation And Stance Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为概念测试报告增加 LLM 原声生成与 stance 校验，在不破坏当前规则稳定性的前提下提升原声自然度。

**Architecture:** 保持 stance 归类由规则层完成，只在 `_build_voice_entry()` 内增加一个 AI 增强层。AI 客户端负责“生成原声”和“校验原声是否与 stance 一致”，概念测试报告层负责 fallback 和最终落盘。

**Tech Stack:** Python, unittest, OpenAI-compatible API

---

### Task 1: Add failing voice-enhancement tests

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py`

**Step 1: Write the failing test**

Add tests for:

```python
def test_voice_entry_uses_llm_quote_when_validation_passes():
    ...

def test_voice_entry_falls_back_when_validation_fails():
    ...

def test_voice_entry_falls_back_when_llm_generation_errors():
    ...
```

**Step 2: Run test to verify it fails**

```powershell
python -m unittest tests.test_concept_testing.SingleConceptTestingTest.test_voice_entry_uses_llm_quote_when_validation_passes tests.test_concept_testing.SingleConceptTestingTest.test_voice_entry_falls_back_when_validation_fails tests.test_concept_testing.SingleConceptTestingTest.test_voice_entry_falls_back_when_llm_generation_errors -v
```

Expected: FAIL because `_build_voice_entry()` still only returns rule-based quotes.

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 2 and Task 3.

**Step 4: Run test to verify it passes**

Re-run after Tasks 2 and 3.

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 2: Add quote-generation and validation methods to AI client

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/ai_clients.py`

**Step 1: Write the failing test**

Covered by Task 1 using stubbed AI client behavior at report layer.

**Step 2: Run test to verify it fails**

Covered by Task 1.

**Step 3: Write minimal implementation**

Implement:

- `BaseAIClient.generate_consumer_quote(...)`
- `BaseAIClient.validate_consumer_quote(...)`
- `OpenAICompatibleClient.generate_consumer_quote(...)`
- `OpenAICompatibleClient.validate_consumer_quote(...)`

Use structured prompt + JSON parsing + fallback return shape.

**Step 4: Run test to verify it passes**

Indirectly verified after Task 3.

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 3: Insert AI-enhanced quote generation into concept report logic

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/concept_testing.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/advanced_testing.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py`

**Step 1: Write the failing test**

Covered by Task 1.

**Step 2: Run test to verify it fails**

Covered by Task 1.

**Step 3: Write minimal implementation**

Implement:

- `ConceptTestRunner(..., ai_client=None)`
- `_build_voice_entry()` uses:
  - rule fallback quote
  - optional LLM quote generation
  - optional LLM validation
  - fallback on failure
- attach `quote_generation_mode` and `quote_validation`
- pass `ai_client` through `AdvancedTestRunner` and `DingTalkBotWorkflow`

**Step 4: Run test to verify it passes**

```powershell
python -m unittest tests.test_concept_testing.SingleConceptTestingTest.test_voice_entry_uses_llm_quote_when_validation_passes tests.test_concept_testing.SingleConceptTestingTest.test_voice_entry_falls_back_when_validation_fails tests.test_concept_testing.SingleConceptTestingTest.test_voice_entry_falls_back_when_llm_generation_errors -v
```

Expected: PASS

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 4: Run focused and regression verification

**Files:**
- No code changes required

**Step 1: Focused tests**

```powershell
python -m unittest tests.test_concept_testing -v
```

Expected: PASS

**Step 2: Broader regression**

```powershell
python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 3: Smoke-test report generation**

```powershell
python .\run_single_concept_report.py
```

Expected: report JSON and HTML generated successfully.

**Step 4: Restart DingTalk bot**

If running:

```powershell
Stop-Process -Id <pid> -Force
python .\run_dingtalk_stream_bot.py
```

Expected: bot reconnects with new voice logic.

**Step 5: Commit**

Repository is not a git repo. Skip commit.
