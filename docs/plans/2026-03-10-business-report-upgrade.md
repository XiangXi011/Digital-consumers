# Business Report Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将当前概念测试报告升级为业务可用版，补足结论依据、原声一致性、可执行建议、可信度提示和正式 HTML 结构。

**Architecture:** 保持现有测试执行链路不变，只升级 `concept_testing.py` 的 report schema 与生成逻辑，以及 `html_report_renderer.py` 的展示模板。核心判断使用规则提取，业务表达用模板化中文输出，确保稳定性和可解释性。

**Tech Stack:** Python, unittest, HTML/CSS

---

### Task 1: Add failing report-schema tests

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py`

**Step 1: Write the failing test**

Add tests for:

```python
def test_runner_generates_business_report_fields():
    ...

def test_voice_of_consumer_entries_include_stance_and_reason_tag():
    ...
```

**Step 2: Run test to verify it fails**

```powershell
python -m unittest tests.test_concept_testing.SingleConceptTestingTest.test_runner_generates_business_report_fields tests.test_concept_testing.SingleConceptTestingTest.test_voice_of_consumer_entries_include_stance_and_reason_tag -v
```

Expected: FAIL because diagnosis/action_plan/report_boundary and aligned voice fields do not exist yet.

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 2.

**Step 4: Run test to verify it passes**

Re-run after Task 2.

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 2: Upgrade report generation logic

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/concept_testing.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py`

**Step 1: Write the failing test**

Covered by Task 1.

**Step 2: Run test to verify it fails**

Covered by Task 1.

**Step 3: Write minimal implementation**

Implement:

- business recommendation translation
- confidence level + reason
- diagnosis block
- segment reasons
- aligned voice entries with `stance_label` and `reason_tag`
- layered action plan
- report boundary block

**Step 4: Run test to verify it passes**

```powershell
python -m unittest tests.test_concept_testing.SingleConceptTestingTest.test_runner_generates_business_report_fields tests.test_concept_testing.SingleConceptTestingTest.test_voice_of_consumer_entries_include_stance_and_reason_tag -v
```

Expected: PASS

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 3: Add failing HTML renderer tests

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Update the renderer-focused test to assert:

- `结论依据拆解`
- `价值主张诊断`
- `下一步动作建议`
- `说明与可信度边界`
- rendered recommendation is business Chinese, not internal enum

**Step 2: Run test to verify it fails**

```powershell
python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_html_renderer_contains_key_visual_sections -v
```

Expected: FAIL because current HTML still exposes internal recommendation and lacks new sections.

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 4.

**Step 4: Run test to verify it passes**

Re-run after Task 4.

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 4: Rebuild the business HTML template

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Covered by Task 3.

**Step 2: Run test to verify it fails**

Covered by Task 3.

**Step 3: Write minimal implementation**

Implement the 10-module HTML structure:

- cover / task info
- one-line conclusion
- diagnosis cards
- KPI overview
- input summary
- segment table with reasons
- buy/reject/conflict section
- aligned quotes
- layered action plan
- confidence boundary

**Step 4: Run test to verify it passes**

```powershell
python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_html_renderer_contains_key_visual_sections -v
```

Expected: PASS

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 5: Run focused and regression verification

**Files:**
- No code changes required

**Step 1: Run focused tests**

```powershell
python -m unittest tests.test_concept_testing tests.test_dingtalk_workflow -v
```

Expected: PASS

**Step 2: Run broader regression**

```powershell
python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 3: Smoke-test a report run**

```powershell
python .\run_single_concept_report.py
```

Expected: report JSON and HTML generated successfully with upgraded structure.

**Step 4: Restart the DingTalk bot**

If running:

```powershell
Stop-Process -Id <pid> -Force
python .\run_dingtalk_stream_bot.py
```

Expected: bot comes back online with new report logic.

**Step 5: Commit**

Repository is not a git repo. Skip commit.
