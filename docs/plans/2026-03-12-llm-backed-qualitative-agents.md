# LLM-Backed Qualitative Agents Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current template-built qualitative workflow with true LLM-backed 8 mother persona agents plus 1 research assistant agent, while failing hard when any required agent output is missing or invalid.

**Architecture:** Keep the DingTalk and LangGraph shell intact, but refactor `qualitative_research.py` into explicit agent orchestration with strict JSON parsing and validation. Mother persona outputs and the research assistant summary must both come from `ai_client.generate_text()` with no fallback acceptance; workflow code should surface incomplete runs as a single user-facing error message instead of partial results.

**Tech Stack:** Python, unittest, LangGraph, OpenAI-compatible text generation, JSON, HTML

---

### Task 1: Write failing runner tests for real agent orchestration

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Add a stub AI client and tests shaped like:

```python
class StubAIClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.is_configured = True

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return self.responses.pop(0)


def test_multi_mode_uses_eight_mom_llm_calls_plus_one_research_assistant(self):
    ai_client = StubAIClient(responses=[... nine live_text JSON payloads ...])
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)
    report = runner.run(QualitativeResearchInput(... mode="multi" ...))
    self.assertEqual(len(ai_client.calls), 9)
    self.assertEqual(len(report["consumer_voice"]), 8)
    self.assertEqual(report["meta"]["agent_count_expected"], 8)
    self.assertEqual(report["meta"]["agent_count_completed"], 8)


def test_single_mode_uses_one_mom_call_plus_one_research_assistant(self):
    ...
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: FAIL because the current runner does not consume the AI client and cannot satisfy the new call-count assertions.

**Step 3: Write minimal implementation**

Do not change production code yet.

**Step 4: Run test to verify it passes**

Re-run after Task 2.

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py'
git commit -m "test: cover llm-backed qualitative agents"
```

### Task 2: Add failing tests for hard failure gating

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Add tests like:

```python
def test_runner_raises_when_any_mom_agent_returns_fallback_mode(self):
    ai_client = StubAIClient(
        responses=[
            {"mode": "live_text", "text": mom_json("M01")},
            {"mode": "fallback_text", "text": "Fallback summary"},
        ]
    )
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)
    with self.assertRaises(IncompleteResearchRunError):
        runner.run(QualitativeResearchInput(mode="single", persona_id="M01", ...))


def test_runner_raises_on_persona_mismatch(self):
    ai_client = StubAIClient(
        responses=[{"mode": "live_text", "text": mom_json("M08")}]
    )
    ...


def test_runner_raises_when_research_assistant_output_is_invalid(self):
    ...
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: FAIL because the current runner accepts local deterministic output and has no strict incomplete-run exception.

**Step 3: Write minimal implementation**

Do not change production code yet.

**Step 4: Run test to verify it passes**

Re-run after Task 3.

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py'
git commit -m "test: add incomplete-run coverage for qualitative agents"
```

### Task 3: Refactor the qualitative runner into explicit LLM agents

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Covered by Tasks 1 and 2.

**Step 2: Run test to verify it fails**

Covered by Tasks 1 and 2.

**Step 3: Write minimal implementation**

Refactor `qualitative_research.py` to include:

```python
class IncompleteResearchRunError(RuntimeError):
    pass


class MomPersonaAgent:
    def __init__(self, persona: dict[str, Any], ai_client: Any):
        self.persona = persona
        self.ai_client = ai_client

    def run(self, research_input: QualitativeResearchInput) -> dict[str, Any]:
        result = self.ai_client.generate_text(
            prompt=self._prompt(research_input),
            system_prompt="You are speaking as one specific Chinese mother consumer persona. Return strict JSON only.",
        )
        if result.get("mode") != "live_text":
            raise IncompleteResearchRunError("Mother agent did not complete with a live LLM response.")
        payload = _parse_json_object(result.get("text", ""))
        _validate_mom_payload(payload, expected_persona_id=self.persona["segment_id"])
        return payload


class ResearchAssistantAgent:
    def __init__(self, ai_client: Any):
        self.ai_client = ai_client

    def run(self, research_input: QualitativeResearchInput, mom_outputs: list[dict[str, Any]]) -> dict[str, list[str]]:
        result = self.ai_client.generate_text(
            prompt=self._prompt(research_input, mom_outputs),
            system_prompt="You are a qualitative research assistant. Return strict JSON only.",
        )
        if result.get("mode") != "live_text":
            raise IncompleteResearchRunError("Research assistant did not complete with a live LLM response.")
        payload = _parse_json_object(result.get("text", ""))
        _validate_summary_payload(payload, mode=research_input.mode)
        return payload
```

`QualitativeResearchRunner.run()` should:

- reject missing or unconfigured `ai_client`
- select the target personas
- run 8 mother agents in multi mode or 1 mother agent in single mode
- count expected and completed mother agents
- run the research assistant only after all mother agents succeed
- return a report with:
  - `meta.agent_count_expected`
  - `meta.agent_count_completed`
  - `meta.completion_status = "complete"`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_qualitative_research -v`

Expected: PASS

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py'
git commit -m "feat: add llm-backed qualitative agents"
```

### Task 4: Surface incomplete runs correctly in the workflow and DingTalk layer

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`

**Step 1: Write the failing test**

Add workflow tests like:

```python
def test_failed_agent_run_returns_incomplete_result_message(self):
    class FailingAIClient:
        is_configured = True
        def generate_text(self, prompt: str, system_prompt: str | None = None):
            return {"mode": "fallback_text", "text": "fallback"}

    bot = DingTalkBotWorkflow(..., ai_client=FailingAIClient())
    ...
    finished = bot.run_pending_task(start["task_id"])
    self.assertEqual(finished["status"], "error")
    self.assertEqual(finished["messages"][0]["content"], "本次结果不完整，请稍后重试")
    self.assertIsNone(finished["html_report_path"])
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v`

Expected: FAIL because the current workflow returns a generic report-generation error and does not distinguish incomplete agent runs.

**Step 3: Write minimal implementation**

In `dingtalk_bot.py`:

- import `IncompleteResearchRunError`
- catch it separately in `run_pending_task()`
- set `session.status = "error"`
- clear `html_report_path` and `json_report_path`
- return only `本次结果不完整，请稍后重试`

Keep generic exception handling for unexpected failures, but the known incomplete-run path should use the exact message above.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v`

Expected: PASS

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py'
git commit -m "feat: surface incomplete qualitative runs"
```

### Task 5: Update reporting and sample runner output to match the new agent metadata

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/run_single_concept_report.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Add assertions like:

```python
self.assertEqual(report["meta"]["completion_status"], "complete")
self.assertEqual(report["meta"]["agent_count_expected"], 8)
self.assertEqual(report["meta"]["agent_count_completed"], 8)
```

If HTML is updated to show agent execution counts, add string assertions for the new labels.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: FAIL because the current report metadata does not include the new completion fields.

**Step 3: Write minimal implementation**

- render the new meta fields if present
- keep `consumer_voice` and `research_summary` layout stable
- keep the sample runner compatible with the LLM-backed runner entrypoint

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_dingtalk_workflow -v`

Expected: PASS

**Step 5: Commit**

```powershell
git add 'C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/run_single_concept_report.py' 'C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py'
git commit -m "feat: add agent completion metadata to reports"
```

### Task 6: Run full verification and restart the DingTalk bot on the new code

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v2_stderr.log`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v2_stdout.log`

**Step 1: Run the targeted unit suite**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: all tests PASS

**Step 2: Run the sample report generator**

Run:

```powershell
python run_single_concept_report.py
```

Expected: success for a fully configured AI client, or a clear incomplete-run failure if the environment is not configured to support live LLM generation.

**Step 3: Restart the DingTalk bot**

Run:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match 'run_dingtalk_stream_bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process -FilePath python -ArgumentList '-u','run_dingtalk_stream_bot.py' -WorkingDirectory 'C:/Users/05537/Desktop/agent/市场部agent teams' -RedirectStandardOutput 'C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stdout.log' -RedirectStandardError 'C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stderr.log'
```

**Step 4: Check the new runtime log**

Run:

```powershell
Get-Content 'C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stderr.log' -Tail 80
```

Expected: DingTalk stream connection opens successfully and no immediate incomplete-run stack trace appears before the next real user message.

**Step 5: Commit**

Do not commit log files. Commit only source changes if any remain:

```powershell
git status --short
```
