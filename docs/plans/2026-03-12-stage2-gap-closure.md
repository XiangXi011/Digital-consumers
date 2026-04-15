# Stage2 Gap Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the current qualitative DingTalk agent from a template-backed Stage1 MVP to a Stage2-ready agent workflow with strict LLM execution, reproducible fingerprints, regression gating, and basic operational hardening.

**Architecture:** Keep the existing DingTalk, LangGraph, and HTML shell, but replace the qualitative core with strict LLM agent orchestration and explicit failure gating. Then add a small Stage2 verification layer: system fingerprint metadata, a file-based golden-set regression command, and runtime/environment checks for the DingTalk stream process. This plan targets Stage2 for the current non-RAG qualitative agent; literal RAG + Agent Stage2 still requires a later retrieval/citation track.

**Tech Stack:** Python, unittest, LangGraph, DingTalk Stream, OpenAI-compatible API, JSON, HTML

---

### Task 1: Add failing tests for strict LLM-backed qualitative orchestration

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Add a reusable stub AI client plus focused tests:

```python
class StubAIClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.is_configured = True

    def generate_text(self, prompt: str, system_prompt: str | None = None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return self.responses.pop(0)


def test_multi_mode_uses_eight_mom_calls_plus_one_summary_call(self):
    ai_client = StubAIClient(responses=[*mom_payloads(8), summary_payload()])
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    report = runner.run(QualitativeResearchInput(... mode="multi" ...))

    self.assertEqual(len(ai_client.calls), 9)
    self.assertEqual(report["meta"]["agent_count_expected"], 8)
    self.assertEqual(report["meta"]["agent_count_completed"], 8)
    self.assertEqual(report["meta"]["completion_status"], "complete")


def test_single_mode_uses_one_mom_call_plus_one_summary_call(self):
    ...
```

Add hard-failure tests too:

```python
def test_runner_raises_when_ai_client_is_missing():
    runner = QualitativeResearchRunner(persona_path, ai_client=None)
    with self.assertRaises(IncompleteResearchRunError):
        runner.run(QualitativeResearchInput(...))


def test_runner_raises_when_any_mom_agent_returns_fallback_mode():
    ...


def test_runner_raises_when_summary_json_is_invalid():
    ...


def test_runner_raises_on_persona_mismatch():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_qualitative_research -v
```

Expected: FAIL because the current runner does not use `ai_client.generate_text()` on the active qualitative path and does not raise an incomplete-run error.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Run test to verify it passes**

Run the same command after Task 2.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py"
git commit -m "test: cover strict qualitative agent orchestration"
```

### Task 2: Implement strict mother-agent and summary-agent orchestration

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Use the failing tests from Task 1**

No new tests here.

**Step 2: Write minimal implementation**

Refactor the runner into explicit agent classes:

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
            system_prompt="You are one specific Chinese mother consumer persona. Return strict JSON only.",
        )
        if result.get("mode") != "live_text":
            raise IncompleteResearchRunError("Mother agent did not complete with a live LLM response.")
        payload = _parse_json_object(result.get("text", ""))
        _validate_mom_payload(payload, expected_persona_id=self.persona["segment_id"])
        return payload


class ResearchAssistantAgent:
    ...
```

Change `QualitativeResearchRunner.run()` to:

- reject missing or unconfigured `ai_client`
- select either 8 personas or 1 persona
- call 1 LLM per mother persona
- call 1 LLM for the research assistant only after all mother agents succeed
- return:
  - `meta.agent_count_expected`
  - `meta.agent_count_completed`
  - `meta.completion_status = "complete"`
- never accept fallback text as a successful qualitative result

Keep the public JSON contract stable where possible, but replace `confidence_note` with validated LLM-backed fields such as `evidence_trace` if needed.

**Step 3: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_qualitative_research -v
```

Expected: PASS.

**Step 4: Run a quick sample smoke**

Run:

```powershell
python -m unittest tests.test_qualitative_research.QualitativeResearchTest.test_multi_mode_returns_eight_mom_responses_and_summary -v
```

Expected: PASS with the new metadata fields asserted.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py"
git commit -m "feat: add strict llm-backed qualitative agents"
```

### Task 3: Add failing workflow tests for incomplete-run handling and Stage2 metadata

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`

**Step 1: Write the failing test**

Add workflow tests shaped like:

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
    self.assertIsNone(finished["json_report_path"])


def test_successful_run_includes_stage2_meta_fields(self):
    ...
    self.assertEqual(report["meta"]["completion_status"], "complete")
    self.assertEqual(report["meta"]["agent_count_expected"], 8)
    self.assertEqual(report["meta"]["agent_count_completed"], 8)
```

Add stream handler coverage too:

```python
def test_handler_sends_incomplete_result_text_on_failed_agent_run(self):
    ...
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: FAIL because the current workflow returns a generic error path and does not enforce the exact incomplete-run contract.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Run test to verify it passes**

Run the same command after Task 4.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py"
git commit -m "test: cover incomplete qualitative run handling"
```

### Task 4: Implement incomplete-run propagation through DingTalk and HTML/report outputs

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`

**Step 1: Use the failing tests from Task 3**

No new tests here.

**Step 2: Write minimal implementation**

In `dingtalk_bot.py`:

```python
from qualitative_research import IncompleteResearchRunError

...
    def run_pending_task(self, task_id: str) -> Dict[str, Any]:
        try:
            state = self.task_graph.invoke({"task_id": task_id})
            return state["response"]
        except IncompleteResearchRunError:
            session = self._load_session_by_task_id(task_id)
            session.status = "error"
            session.html_report_path = None
            session.json_report_path = None
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "本次结果不完整，请稍后重试"}],
                html_report_path=None,
                json_report_path=None,
            )
```

In `html_report_renderer.py`, display the new meta fields if present:

```python
meta_rows.append(("Completion Status", meta.get("completion_status", "")))
meta_rows.append(("Agent Count", f"{meta.get('agent_count_completed', 0)}/{meta.get('agent_count_expected', 0)}"))
```

Do not render HTML for failed runs.

**Step 3: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS.

**Step 4: Run the full current targeted suite**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py" "C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py" "C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py"
git commit -m "feat: surface incomplete qualitative runs"
```

### Task 5: Add failing tests for Stage2 system fingerprint metadata

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`

**Step 1: Write the failing test**

Add assertions for a minimal Stage2 fingerprint:

```python
def test_report_contains_minimal_system_fingerprint(self):
    ai_client = StubAIClient(responses=[*mom_payloads(8), summary_payload()])
    runner = QualitativeResearchRunner(persona_path, ai_client=ai_client)

    report = runner.run(QualitativeResearchInput(...))

    fingerprint = report["meta"]["system_fingerprint"]
    self.assertEqual(fingerprint["git_sha"], "test-sha")
    self.assertEqual(fingerprint["env"], "test")
    self.assertEqual(fingerprint["model_id"], "stub-model")
    self.assertTrue(report["meta"]["schema_version"])
```

Inject deterministic values by stubbing a helper or by passing a metadata provider into the runner.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow -v
```

Expected: FAIL because the current report meta does not include system fingerprint data.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Run test to verify it passes**

Run the same command after Task 6.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py"
git commit -m "test: cover stage2 report fingerprint metadata"
```

### Task 6: Implement Stage2 report fingerprint and schema versioning

**Files:**
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/system_fingerprint.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/ai_clients.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Use the failing tests from Task 5**

No new tests here.

**Step 2: Write minimal implementation**

Create a tiny helper:

```python
from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class SystemFingerprint:
    git_sha: str
    env: str
    model_id: str
    prompt_version: str
    schema_version: str = "qualitative-report-v2"


def collect_system_fingerprint(base_dir: Path, ai_client: Any | None = None) -> dict[str, str]:
    ...
```

Populate:

- `git_sha`
- `env` from env var or default `dev`
- `model_id` from AI client config if present
- `prompt_version` as an explicit constant for the qualitative prompt set
- `schema_version`

Store this under `report["meta"]["system_fingerprint"]`.

**Step 3: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow -v
```

Expected: PASS.

**Step 4: Run the full qualitative suite again**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/system_fingerprint.py" "C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py" "C:/Users/05537/Desktop/agent/市场部agent teams/ai_clients.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py"
git commit -m "feat: add stage2 system fingerprint metadata"
```

### Task 7: Add failing tests for a golden-set regression gate

**Files:**
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py`
- Test: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py`

**Step 1: Write the failing test**

Create tests for a small file-based regression runner:

```python
def test_regression_runner_writes_metrics_json(tmp_path):
    report_path = tmp_path / "regression.json"
    exit_code = run_regression(
        golden_set_path=golden_path,
        output_path=report_path,
        ai_client=StubAIClient(responses=...),
    )
    assert exit_code == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"]["case_count"] == 3
    assert payload["summary"]["completion_rate"] == 1.0
    assert payload["summary"]["schema_valid_rate"] == 1.0


def test_regression_runner_returns_nonzero_when_threshold_is_breached(tmp_path):
    ...
```

The runner should evaluate:

- completion rate
- schema-valid rate
- persona-match rate
- summary-section completeness

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_qualitative_regression -v
```

Expected: FAIL because no regression runner exists yet.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Run test to verify it passes**

Run the same command after Task 8.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py"
git commit -m "test: add qualitative regression gate coverage"
```

### Task 8: Implement a file-based Stage2 regression gate and golden set

**Files:**
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/golden_sets/qualitative_stage2_cases.json`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/run_qualitative_regression.py`
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py`

**Step 1: Use the failing tests from Task 7**

No new tests here.

**Step 2: Write minimal implementation**

Create a small JSON golden set:

```json
[
  {
    "id": "copy-feedback-multi-001",
    "input": {
      "mode": "multi",
      "question_type": "copy_feedback",
      "user_question": "Which message is most credible?"
    },
    "expected": {
      "mode": "multi",
      "agent_count": 8
    }
  }
]
```

Create a runner that emits:

```json
{
  "generated_at": "ISO8601",
  "summary": {
    "case_count": 10,
    "completion_rate": 0.9,
    "schema_valid_rate": 1.0,
    "persona_match_rate": 1.0,
    "gate_passed": true
  },
  "cases": [...]
}
```

Use a nonzero process exit when thresholds fail:

```python
if summary["completion_rate"] < 1.0:
    return 1
```

**Step 3: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_qualitative_regression -v
```

Expected: PASS.

**Step 4: Run the gate command manually**

Run:

```powershell
python run_qualitative_regression.py --golden-set "C:/Users/05537/Desktop/agent/市场部agent teams/golden_sets/qualitative_stage2_cases.json" --output "C:/Users/05537/Desktop/agent/市场部agent teams/outputs/qualitative_regression_report.json"
```

Expected: JSON report is written and the process exits `0` on success.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/golden_sets/qualitative_stage2_cases.json" "C:/Users/05537/Desktop/agent/市场部agent teams/run_qualitative_regression.py" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py"
git commit -m "feat: add stage2 qualitative regression gate"
```

### Task 9: Add runtime preflight checks and reproducible dependency pins for the DingTalk bot

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_stream_service.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/run_dingtalk_stream_bot.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/requirements.txt`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`

**Step 1: Write the failing test**

Add tests for a preflight validator:

```python
def test_preflight_rejects_known_bad_python_runtime_combo(self):
    warning = validate_runtime_environment(
        python_version="3.14.0",
        dingtalk_stream_version="...",
        websockets_version="...",
    )
    self.assertIn("unsupported", warning.lower())


def test_start_forever_raises_clear_error_when_required_credentials_are_missing(self):
    ...
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_dingtalk_stream_service -v
```

Expected: FAIL because no runtime preflight exists yet.

**Step 3: Write minimal implementation**

Add:

```python
def validate_runtime_environment(...) -> str:
    ...


class DingTalkStreamBotService:
    ...
    def start_forever(self):
        warning = validate_runtime_environment(...)
        if warning:
            raise RuntimeError(warning)
        self.client.start_forever()
```

Expand `requirements.txt` into a real pinned runtime manifest for the app, including the DingTalk and OpenAI stack actually used in this repo.

**Step 4: Run tests and a startup smoke**

Run:

```powershell
python -m unittest tests.test_dingtalk_stream_service -v
python run_dingtalk_stream_bot.py
```

Expected: tests PASS; startup either succeeds or fails immediately with a clear compatibility/preflight message instead of a noisy async stack trace.

**Step 5: Commit**

```powershell
git add "C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_stream_service.py" "C:/Users/05537/Desktop/agent/市场部agent teams/run_dingtalk_stream_bot.py" "C:/Users/05537/Desktop/agent/市场部agent teams/requirements.txt" "C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py"
git commit -m "feat: harden dingtalk runtime startup"
```

### Task 10: Run the full Stage2 verification bundle

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/outputs/qualitative_regression_report.json`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stdout.log`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stderr.log`

**Step 1: Run the full test suite for the qualitative path**

Run:

```powershell
python -m unittest tests.test_qualitative_research tests.test_dingtalk_workflow tests.test_dingtalk_stream_service tests.test_qualitative_regression -v
```

Expected: all PASS.

**Step 2: Run the regression gate**

Run:

```powershell
python run_qualitative_regression.py --golden-set "C:/Users/05537/Desktop/agent/市场部agent teams/golden_sets/qualitative_stage2_cases.json" --output "C:/Users/05537/Desktop/agent/市场部agent teams/outputs/qualitative_regression_report.json"
```

Expected: process exit `0` and gate report written.

**Step 3: Restart the DingTalk bot on the new code**

Run:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match 'run_dingtalk_stream_bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process -FilePath python -ArgumentList '-u','run_dingtalk_stream_bot.py' -WorkingDirectory 'C:/Users/05537/Desktop/agent/市场部agent teams' -RedirectStandardOutput 'C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stdout.log' -RedirectStandardError 'C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stderr.log'
```

**Step 4: Check the runtime log**

Run:

```powershell
Get-Content 'C:/Users/05537/Desktop/agent/市场部agent teams/outputs/logs/dingtalk_stream_live_v3_stderr.log' -Tail 80
```

Expected: no immediate compatibility failure or incomplete-run stack trace before the next real user request.

**Step 5: Commit**

Do not commit generated logs or reports. Commit only source changes if any remain:

```powershell
git status --short
```

---

## Literal RAG Note

This plan does **not** make the project pass the `verify-agent-rag-playbook` literally as a RAG + Agent system. To satisfy that stricter target later, add a separate retrieval/citation track:

- retrieval configuration and source store
- citation rendering in HTML and DingTalk outputs
- grounding tests and citation coverage metrics
- prompt-injection and unauthorized-access tests for retrieved context
- retrieval-aware regression gates
