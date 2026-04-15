# Qualitative Research Assistant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the concept-testing workflow with a 9-agent qualitative research assistant while backing up the legacy implementation and preserving DingTalk, HTML, and JSON outputs.

**Architecture:** Create a new `qualitative_research.py` domain layer that loads the existing 8 mother personas, generates structured persona responses, and builds a fixed research-assistant summary. Rebuild the session manager, LangGraph workflow, DingTalk workflow, and HTML renderer around a research brief schema while keeping the DingTalk entrypoint and report publishing contract stable. Copy the current concept-testing workflow into `legacy_concept_testing_backup/` before any behavior changes.

**Tech Stack:** Python, unittest, LangGraph, HTML/CSS, JSON

---

### Task 1: Snapshot the legacy workflow into a backup folder

**Files:**
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/README.md`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/advanced_testing.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/concept_testing.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/dingtalk_bot.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/html_report_renderer.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_flows.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_nodes.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_state.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/run_single_concept_report.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/task_session_manager.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_advanced_testing.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_concept_testing.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_dingtalk_workflow.py`

**Step 1: Write the backup manifest**

Create `C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/README.md` with:

```markdown
# Legacy Concept Testing Backup

This folder stores the last concept-testing implementation before the qualitative research assistant rewrite on 2026-03-11.

Copied files:
- advanced_testing.py
- concept_testing.py
- dingtalk_bot.py
- html_report_renderer.py
- langgraph_flows.py
- langgraph_nodes.py
- langgraph_state.py
- run_single_concept_report.py
- task_session_manager.py
- tests/test_advanced_testing.py
- tests/test_concept_testing.py
- tests/test_dingtalk_workflow.py
```

**Step 2: Verify the backup folder does not already contain stale copies**

Run: `Get-ChildItem 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup' -Recurse`

Expected: either no files yet or only the new `README.md`

**Step 3: Copy the legacy files**

Run:

```powershell
New-Item -ItemType Directory -Force 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/advanced_testing.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/advanced_testing.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/concept_testing.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/concept_testing.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/dingtalk_bot.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/html_report_renderer.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_flows.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_flows.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_nodes.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_state.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_state.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/run_single_concept_report.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/run_single_concept_report.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/task_session_manager.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_advanced_testing.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_advanced_testing.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_concept_testing.py'
Copy-Item 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_dingtalk_workflow.py'
```

**Step 4: Verify every required file exists in the backup**

Run:

```powershell
$paths = @(
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/advanced_testing.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/concept_testing.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/dingtalk_bot.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/html_report_renderer.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_flows.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_nodes.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/langgraph_state.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/run_single_concept_report.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/task_session_manager.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_advanced_testing.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_concept_testing.py',
  'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup/tests/test_dingtalk_workflow.py'
)
$paths | ForEach-Object { '{0}: {1}' -f $_, (Test-Path $_) }
```

Expected: every line ends with `True`

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/legacy_concept_testing_backup'
git commit -m "chore: back up legacy concept testing workflow"
```

### Task 2: Replace the old runner tests with failing qualitative runner tests

**Files:**
- Delete: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py`
- Delete: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_advanced_testing.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Create `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py` with tests shaped like:

```python
def test_multi_mode_returns_eight_mom_responses_and_summary(self):
    request = module.QualitativeResearchInput(
        mode="multi",
        question_type="purchase_decision",
        user_question="8类妈妈会不会买，最大顾虑是什么？",
        product_info="儿童牙膏，主打低氟防蛀和孩子更愿意坚持刷牙",
    )
    report = runner.run(request)
    assert report["meta"]["mode"] == "multi"
    assert len(report["consumer_voice"]) == 8
    assert sorted(report["research_summary"].keys()) == [
        "barriers",
        "consensus",
        "copy_insights",
        "differences",
        "drivers",
        "pain_points",
        "recommendations",
    ]

def test_single_mode_returns_only_selected_persona(self):
    request = module.QualitativeResearchInput(
        mode="single",
        question_type="copy_feedback",
        persona_id="M04",
        user_question="高线忙碌妈会被哪句话打动？",
        copy_material="专业防蛀，孩子喜欢，妈妈省心",
    )
    report = runner.run(request)
    assert report["meta"]["mode"] == "single"
    assert len(report["consumer_voice"]) == 1
    assert report["consumer_voice"][0]["persona_id"] == "M04"
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: FAIL with import or attribute errors because `qualitative_research.py` does not exist yet

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 3.

**Step 4: Run test to verify it passes**

Re-run after Task 3.

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_concept_testing.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_advanced_testing.py'
git commit -m "test: add qualitative runner coverage"
```

### Task 3: Implement the qualitative research domain layer

**Files:**
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Covered by Task 2.

**Step 2: Run test to verify it fails**

Covered by Task 2.

**Step 3: Write minimal implementation**

Create `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py` with a structure like:

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import json

SUMMARY_KEYS = [
    "consensus",
    "differences",
    "pain_points",
    "drivers",
    "barriers",
    "copy_insights",
    "recommendations",
]

@dataclass
class QualitativeResearchInput:
    mode: str
    question_type: str
    user_question: str
    persona_id: str = ""
    background_material: str = ""
    product_info: str = ""
    copy_material: str = ""
    attachments: list[str] = field(default_factory=list)
    follow_up_context: str = ""

class QualitativeResearchRunner:
    def __init__(self, persona_path: Path | str, ai_client: Any | None = None):
        self.persona_path = Path(persona_path)
        self.ai_client = ai_client
        self.personas = self._load_personas()

    def run(self, research_input: QualitativeResearchInput) -> dict[str, Any]:
        selected = self._select_personas(research_input)
        consumer_voice = [self._build_persona_response(persona, research_input) for persona in selected]
        summary = self._build_summary(consumer_voice, research_input)
        return {
            "meta": {
                "mode": research_input.mode,
                "question_type": research_input.question_type,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_agents": len(consumer_voice),
            },
            "research_brief": {
                "user_question": research_input.user_question,
                "product_info": research_input.product_info,
                "copy_material": research_input.copy_material,
                "background_material": research_input.background_material,
            },
            "consumer_voice": consumer_voice,
            "research_summary": summary,
            "appendix": {
                "selected_persona": research_input.persona_id or None,
                "follow_up_context": research_input.follow_up_context,
                "attachments": list(research_input.attachments),
            },
        }
```

Implement `_load_personas`, `_select_personas`, `_build_persona_response`, and `_build_summary` so that:

- multi mode returns one response per segment for 8 total responses
- single mode returns only the requested persona
- every response contains `persona_id`, `persona_name`, `question_type`, `stance`, `core_needs`, `motivations`, `concerns`, `decision_logic`, `verbatim_answer`, and `confidence_note`
- `research_summary` always contains the seven fixed keys
- when `ai_client` is unavailable, fallback text is deterministic and testable

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: PASS

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py'
git commit -m "feat: add qualitative research runner"
```

### Task 4: Replace the old DingTalk workflow tests with failing research-brief tests

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`

**Step 1: Write the failing test**

Replace the concept-checklist assertions with qualitative-workflow tests such as:

```python
def test_first_contact_returns_research_brief_checklist(self):
    result = bot.handle_message({...})
    self.assertEqual(result["status"], "collecting")
    self.assertIn("研究任务信息清单", result["messages"][0]["content"])
    self.assertIn("模式", result["messages"][0]["content"])
    self.assertIn("研究问题", result["messages"][0]["content"])

def test_single_mode_without_persona_requests_follow_up(self):
    result = bot.handle_message({
        "text": "单人模式，帮我看看这句文案有没有吸引力"
    })
    self.assertEqual(result["status"], "collecting")
    self.assertIn("请指定妈妈画像", result["messages"][0]["content"])

def test_multi_mode_can_run_and_return_report_paths(self):
    ...
```

Update the stream-service tests so their fake workflow messages and markdown text assert against the new qualitative labels instead of old concept-testing wording.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: FAIL because the session manager and workflow still collect concept-testing fields

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 5.

**Step 4: Run test to verify it passes**

Re-run after Task 5.

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py'
git commit -m "test: cover qualitative workflow collection"
```

### Task 5: Rebuild the session manager and LangGraph workflow around research briefs

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_state.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_flows.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/run_single_concept_report.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`

**Step 1: Write the failing test**

Covered by Task 4.

**Step 2: Run test to verify it fails**

Covered by Task 4.

**Step 3: Write minimal implementation**

In `task_session_manager.py`:

- replace the old field list with research-brief fields:

```python
FIELD_SPECS = [
    {"key": "mode", "label": "模式", "priority": "P0"},
    {"key": "question_type", "label": "研究问题", "priority": "P0"},
    {"key": "persona_id", "label": "指定妈妈画像", "priority": "P0"},
    {"key": "user_question", "label": "用户问题", "priority": "P0"},
    {"key": "background_material", "label": "背景资料", "priority": "P1"},
    {"key": "product_info", "label": "产品信息", "priority": "P1"},
    {"key": "copy_material", "label": "文案或卖点", "priority": "P1"},
]
```

- add inference helpers:
  - `infer_mode`
  - `infer_question_type`
  - `infer_persona_id`
- make `has_minimum_runnable_info` require `mode`, `question_type`, and `user_question`, plus `persona_id` for single mode
- keep attachments and session reset behavior

In `langgraph_state.py`, replace concept-testing state keys with:

```python
class AnalysisGraphState(TypedDict, total=False):
    research_input: Any
    selected_personas: list[dict[str, Any]]
    consumer_voice: list[dict[str, Any]]
    research_summary: dict[str, Any]
    report: dict[str, Any]
    html: str
    error: str
```

In `langgraph_nodes.py` and `langgraph_flows.py`:

- remove the old evaluation / discussion / deep-dive nodes
- add nodes for:
  - build research input
  - run qualitative research
  - render HTML
  - persist outputs
  - publish report
  - finalize response

In `dingtalk_bot.py`:

- replace `ConceptTestRunner` and `AdvancedTestRunner` with `QualitativeResearchRunner`
- update `_build_short_summary` to summarize `research_summary`
- keep the existing response contract with `status`, `task_id`, `messages`, `html_report_path`, `json_report_path`, and `public_report_url`

In `run_single_concept_report.py`:

- keep the filename for operator familiarity
- replace the sample run with a qualitative multi-mode example that writes the new JSON/HTML report

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_state.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_flows.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/run_single_concept_report.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py'
git commit -m "feat: switch workflow to qualitative research briefs"
```

### Task 6: Add failing HTML renderer tests for the new report structure

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Add or update the renderer assertions to check for:

```python
self.assertIn("消费者原声", html)
self.assertIn("研究总结", html)
self.assertIn("共识", html)
self.assertIn("分歧", html)
self.assertIn("痛点", html)
self.assertIn("驱动", html)
self.assertIn("障碍", html)
self.assertIn("启发", html)
self.assertIn("建议", html)
self.assertNotIn("estimated_conversion_rate", html)
self.assertNotIn("segment_opportunity", html)
self.assertNotIn("purchase_intent", html)
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_html_renderer_contains_key_visual_sections -v`

Expected: FAIL because the renderer still emits the legacy report structure

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 7.

**Step 4: Run test to verify it passes**

Re-run after Task 7.

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py'
git commit -m "test: assert qualitative html report structure"
```

### Task 7: Rebuild the HTML renderer for consumer voice plus research summary

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Covered by Task 6.

**Step 2: Run test to verify it fails**

Covered by Task 6.

**Step 3: Write minimal implementation**

Rebuild `render()` so it consumes:

- `report["meta"]`
- `report["research_brief"]`
- `report["consumer_voice"]`
- `report["research_summary"]`
- `report["appendix"]`

Render these sections:

- task overview
- mode and question type chips
- original question and supporting materials
- mother persona cards
- research summary cards for `consensus`, `differences`, `pain_points`, `drivers`, `barriers`, `copy_insights`, and `recommendations`
- appendix and follow-up context

Add helper methods that keep the renderer deterministic:

```python
def _persona_cards(self, items: list[dict[str, Any]]) -> str: ...
def _summary_block(self, title: str, items: list[str]) -> str: ...
def _brief_value(self, value: str) -> str: ...
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_html_renderer_contains_key_visual_sections -v`

Expected: PASS

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py'
git commit -m "feat: render qualitative research reports"
```

### Task 8: Run focused verification and regression checks

**Files:**
- No code changes required

**Step 1: Run focused tests**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 2: Run remaining active regression tests**

Run:

```powershell
python -m unittest tests.test_generate_personas_constraints -v
```

Expected: PASS

**Step 3: Smoke-test the local sample report**

Run: `python 'C:/Users/05537/Desktop/agent/市场部agent teams/run_single_concept_report.py'`

Expected: JSON and HTML outputs are written using the qualitative report schema

**Step 4: Smoke-test the DingTalk workflow without the stream daemon**

Run:

```powershell
@'
from pathlib import Path
from dingtalk_bot import DingTalkBotWorkflow

base = Path(r"C:/Users/05537/Desktop/agent/市场部agent teams")
workflow = DingTalkBotWorkflow(
    persona_path=base / "persona_samples_complete.json",
    session_dir=base / "outputs" / "dingtalk_sessions",
    output_dir=base / "outputs" / "dingtalk_reports",
)
result = workflow.handle_message(
    {
        "group_id": "group-1",
        "conversation_id": "conv-1",
        "user_id": "user-1",
        "text": "多人模式，购买决策：这款儿童牙膏8类妈妈会不会买，最大顾虑是什么？",
    }
)
print(result["status"])
print(result["messages"][0]["content"])
'@ | python -
```

Expected: status is `running` or `awaiting_run_confirmation` with qualitative research wording, not concept-testing wording

**Step 5: Commit**

```powershell
git status --short
```

Expected: no unexpected changes remain before the final integration decision
