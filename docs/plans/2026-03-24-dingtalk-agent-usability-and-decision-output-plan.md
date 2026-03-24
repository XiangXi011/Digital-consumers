# DingTalk Agent Usability And Decision Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the DingTalk agent easier to brief, make the 8 personas react like distinct instinctive consumers, and replace low-value summaries with a decision card the business can act on.

**Architecture:** Keep the hardened workflow shell (`BusinessBrief`, authorization, follow-up isolation, reporting pipeline), but loosen the business layer. Intake should accept messy mixed-source briefs, persona generation should move from rubric-first to instinct-first, and synthesis should produce a stable `decision_frame` plus a user-facing `decision_card`. Compatibility fields can remain during migration, but they stop being the product surface.

**Tech Stack:** Python, LangGraph workflow nodes, Pydantic models, existing OCR / vision helpers in `ai_clients.py`, unittest / pytest regression tests, YAML persona assets

---

## File Map

- `C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py`
  Intake parsing, first-turn session updates, source link extraction, question bundle extraction, field normalization.
- `C:/Users/05537/Desktop/agent/市场部agent teams/business_brief.py`
  Typed business context projected downstream from intake, including compatibility support for source links and custom questions.
- `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
  Workflow ingress, first-turn handling, attachment enrichment, follow-up context persistence, task completion payload wiring.
- `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
  DingTalk-facing completion message generation and short summary replacement with decision-card content.
- `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_stream_service.py`
  Attachment capture remains here; only touch if the workflow needs extra event metadata for source links or images.
- `C:/Users/05537/Desktop/agent/市场部agent teams/ai_clients.py`
  Reuse existing OCR / vision extraction helpers; avoid adding new APIs unless current helpers are insufficient.
- `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
  Persona prompt schema, persona validation, evidence extraction, synthesis, `decision_frame`, `decision_card`, compatibility output.
- `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`
  HTML top section redesign from summary-first to decision-memo-first.
- `C:/Users/05537/Desktop/agent/市场部agent teams/personas/*.yaml`
  Persona behavioral guidance migration from hard scoring weights to soft triggers and decision heuristics.
- `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
  End-to-end workflow regressions for first-turn parsing, task completion, and follow-up behavior.
- `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`
  DingTalk transport / markdown regressions for completion messages and report links.
- `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
  Persona and synthesis contract regressions.
- `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py`
  Output-shape and renderer compatibility regressions.
- `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_final_lock_contract.py`
  Keep contract-safe checks around `BusinessBrief` and workflow boundaries while extending payload shape.
- `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_persona_math_decoupling.py`
  Either demote or narrow this suite so purchase scoring remains compatibility-only metadata instead of the main persona driver.

## Execution Notes

- The worktree is currently dirty. During implementation, stage only files listed in the active task.
- Do not delete compatibility fields (`research_summary`, `structured_recommendation`, backend evaluation metadata) until the replacement decision-card tests pass.
- Prefer adding new tests before deleting old ones so migration remains reversible.

### Task 1: Make first-turn intake parse real user briefs

**Files:**
- Create: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_task_session_manager.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/business_brief.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:
- a brand-new session parses the user's first full message before replying with any helper checklist
- a mixed brief containing `产品信息`, `文案或卖点`, and multiple question groups preserves the original questions in order
- source links from ecommerce text are preserved instead of being dropped

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run:
- `python -m pytest tests/test_task_session_manager.py tests/test_dingtalk_workflow.py -q`

Expected:
- FAIL because new sessions still route to `send_checklist` before ingesting the first message
- FAIL because source links / question bundles are not stored in the current session or brief shape

- [ ] **Step 3: Implement the minimal intake changes**

Implement:
- parse first-turn user text before deciding whether to send a helper checklist
- add source-link extraction in `TaskSessionManager`
- add question-bundle extraction so multiple user-authored questions survive intake
- extend `BusinessBrief` with compatibility fields for `source_links` and `custom_questions`

- [ ] **Step 4: Run the targeted tests to confirm pass**

Run:
- `python -m pytest tests/test_task_session_manager.py tests/test_dingtalk_workflow.py -q`

Expected:
- PASS for first-turn parsing, source-link preservation, and custom-question capture

- [ ] **Step 5: Commit**

Run:
- `git add tests/test_task_session_manager.py tests/test_dingtalk_workflow.py task_session_manager.py langgraph_nodes.py business_brief.py`
- `git commit -m "feat: parse first-turn briefs and preserve custom questions"`

### Task 2: Enrich intake from attachments, OCR, and mixed-source product info

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_final_lock_contract.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/business_brief.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/ai_clients.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:
- when an attachment path is present, the workflow attempts product-field extraction before readiness gating
- extracted OCR fields can fill missing `product_info`, `copy_material`, or brand/category context
- mixed-source input can combine typed product text with extracted image signals without overwriting typed user facts

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run:
- `python -m pytest tests/test_dingtalk_workflow.py tests/test_final_lock_contract.py -q`

Expected:
- FAIL because attachments are currently passed through as file paths only
- FAIL because extracted fields are not merged into the business brief

- [ ] **Step 3: Implement the minimal enrichment path**

Implement:
- a workflow-side enrichment hook that calls `extract_product_fields_from_image`
- session merge logic that prefers explicit user text over OCR guesses
- `BusinessBrief` projection that can assemble product context from typed text, OCR text, and source-link context

- [ ] **Step 4: Run the targeted tests to confirm pass**

Run:
- `python -m pytest tests/test_dingtalk_workflow.py tests/test_final_lock_contract.py -q`

Expected:
- PASS for attachment enrichment and mixed-source brief assembly

- [ ] **Step 5: Commit**

Run:
- `git add tests/test_dingtalk_workflow.py tests/test_final_lock_contract.py langgraph_nodes.py task_session_manager.py business_brief.py ai_clients.py`
- `git commit -m "feat: enrich intake from attachments and mixed product sources"`

### Task 3: Replace rubric-first personas with instinct-first personas

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_persona_math_decoupling.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M01.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M02.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M03.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M04.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M05.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M06.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M07.yaml`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/personas/M08.yaml`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:
- persona payloads can validate with instinct-first fields (`instant_feeling`, `default_action`, `gut_stance`, `emotional_trigger`, `posthoc_reasoning`, `switch_condition`, `verbatim_answer`)
- personas no longer require shared rubric scores to be considered valid
- different personas can produce different default actions under the same incomplete product brief

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run:
- `python -m pytest tests/test_qualitative_research.py tests/test_persona_math_decoupling.py -q`

Expected:
- FAIL because `_validate_mom_payload` currently requires rubric scores and shared evaluation framing

- [ ] **Step 3: Implement the minimal persona migration**

Implement:
- instinct-first persona prompt instructions in `qualitative_research.py`
- a new validation schema for reaction-first persona fields
- compatibility mapping so old renderer / evidence code still has enough fields during migration
- persona YAML updates from hard weights / vetoes toward emotional triggers, decision path, low-info heuristics, and voice style

- [ ] **Step 4: Run the targeted tests to confirm pass**

Run:
- `python -m pytest tests/test_qualitative_research.py tests/test_persona_math_decoupling.py -q`

Expected:
- PASS for instinct-first persona validation and narrowed math-decoupling expectations

- [ ] **Step 5: Commit**

Run:
- `git add tests/test_qualitative_research.py tests/test_persona_math_decoupling.py qualitative_research.py personas/M01.yaml personas/M02.yaml personas/M03.yaml personas/M04.yaml personas/M05.yaml personas/M06.yaml personas/M07.yaml personas/M08.yaml`
- `git commit -m "feat: make persona reactions instinct-first"`

### Task 4: Add decision-frame synthesis and answer user-authored questions

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_final_lock_contract.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/qualitative_research.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/evidence_models.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:
- every completed run returns `decision_frame` and `decision_card`
- incomplete information still yields one explicit recommendation
- multi-persona disagreement still yields one explicit recommendation plus audience prioritization
- `decision_card.question_answers` answers the user's actual custom questions instead of generic placeholders

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run:
- `python -m pytest tests/test_qualitative_research.py tests/test_qualitative_regression.py tests/test_final_lock_contract.py -q`

Expected:
- FAIL because the current synthesizer only returns `research_summary` and `structured_recommendation`

- [ ] **Step 3: Implement the minimal decision-output layer**

Implement:
- `decision_frame` built from persona evidence and audience fit
- `decision_card` generation in synthesis
- compatibility population for `research_summary` / `structured_recommendation` so old consumers still work during migration
- mapping from `custom_questions` to concise `question_answers`

- [ ] **Step 4: Run the targeted tests to confirm pass**

Run:
- `python -m pytest tests/test_qualitative_research.py tests/test_qualitative_regression.py tests/test_final_lock_contract.py -q`

Expected:
- PASS for explicit recommendation output and question-answer support

- [ ] **Step 5: Commit**

Run:
- `git add tests/test_qualitative_research.py tests/test_qualitative_regression.py tests/test_final_lock_contract.py qualitative_research.py evidence_models.py`
- `git commit -m "feat: add decision-card synthesis and question answers"`

### Task 5: Redesign DingTalk and HTML output around the decision card

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_qualitative_regression.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_bot.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/html_report_renderer.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove:
- DingTalk completion messages include the recommendation, rationale, key evidence, audience priority, immediate action, and report link
- follow-up context stores the prior decision summary instead of a vague research summary string
- the HTML report top section renders a decision memo before persona detail cards

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run:
- `python -m pytest tests/test_dingtalk_stream_service.py tests/test_dingtalk_workflow.py tests/test_qualitative_regression.py -q`

Expected:
- FAIL because the current output still begins with `简版结论`
- FAIL because the HTML renderer still leads with summary-oriented sections

- [ ] **Step 3: Implement the minimal presentation changes**

Implement:
- a `decision_card` formatter in `dingtalk_bot.py`
- follow-up summary persistence based on the recommendation, not the old summary sentence
- an HTML top section for decision, evidence, audience fit, and immediate action

- [ ] **Step 4: Run the targeted tests to confirm pass**

Run:
- `python -m pytest tests/test_dingtalk_stream_service.py tests/test_dingtalk_workflow.py tests/test_qualitative_regression.py -q`

Expected:
- PASS for DingTalk completion text and HTML decision memo rendering

- [ ] **Step 5: Commit**

Run:
- `git add tests/test_dingtalk_stream_service.py tests/test_dingtalk_workflow.py tests/test_qualitative_regression.py dingtalk_bot.py langgraph_nodes.py html_report_renderer.py`
- `git commit -m "feat: render decision cards in DingTalk and HTML"`

### Task 6: Run migration-safe verification

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/run_qualitative_regression.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/e2e_validation_test.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/docs/plans/2026-03-24-dingtalk-agent-usability-and-decision-output-design.md`

- [ ] **Step 1: Update scripted verification to check decision-card output**

Add or update checks so regression scripts verify:
- explicit recommendation presence
- question-answer presence
- compatibility fields still exist where required

- [ ] **Step 2: Run focused verification**

Run:
- `python -m pytest tests/test_task_session_manager.py tests/test_dingtalk_workflow.py tests/test_dingtalk_stream_service.py tests/test_final_lock_contract.py tests/test_qualitative_research.py tests/test_qualitative_regression.py -q`

Expected:
- PASS for all newly changed surfaces

- [ ] **Step 3: Run the full suite**

Run:
- `python -m pytest tests -q`

Expected:
- PASS with no new regressions

- [ ] **Step 4: Run the lightweight regression script**

Run:
- `python run_qualitative_regression.py`

Expected:
- decision-card assertions pass

- [ ] **Step 5: Commit**

Run:
- `git add run_qualitative_regression.py e2e_validation_test.py docs/plans/2026-03-24-dingtalk-agent-usability-and-decision-output-design.md`
- `git commit -m "test: verify decision-card migration"`
