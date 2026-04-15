# Business Brief State Machine Design

**Date:** 2026-03-13

## Goal

Replace the current field-driven DingTalk intake flow with a business-first intake model that:

- normalizes natural-language requests into a single `BusinessBrief`
- routes every request through one `ReadinessGate`
- explicitly handles downgrade and assumption-based execution
- separates internal workflow state from business-facing DingTalk messages
- returns recoverable failure guidance instead of generic retry text

## Problem Summary

The current implementation has the wrong abstraction boundary at the intake layer. It asks users for technical fields such as `mode`, `question_type`, and `persona_id`, then infers execution from partially normalized text. This causes:

- task misclassification, especially when “selling points” are treated as copy testing
- incomplete extraction of product facts from natural-language business input
- inconsistent minimum runnable checks across different branches
- authorization phrases that do not reliably unlock execution
- assumption mode that is only a prompt, not an execution input
- hidden downgrade behavior or hard failure where graceful fallback is possible
- technical error text leaking into business-facing replies

This is not a single bug. It is an intake-model and state-machine design issue.

## Design Principles

1. Business-first intake
   The system should consume business natural language, not ask the market team to fill internal fields.

2. Single internal intermediate model
   `BusinessBrief` becomes the only business-task object shared across intake, readiness, planning, dispatch, and recovery.

3. Single execution gate
   `ReadinessGate` is the only place allowed to decide whether the system can run, should downgrade, or must ask follow-up questions.

4. Explicit downgrade
   Downgrades must be recorded internally and explained to the user in business language.

5. Real assumption mode
   Assumptions must be persisted in the brief, consumed by planner/agents, and visible in the final output.

6. Display isolation
   All user-facing DingTalk text must pass through `UserMessagePresenter`. Internal schema values must never leak directly.

7. Recoverable failures
   Failures must identify the failed stage, explain the reason, preserve context, and tell the user what to reply next.

## Scope

### In Scope

- business natural-language parsing
- task-type normalization
- structured fact extraction
- unified readiness evaluation
- execution authorization normalization
- explicit downgrade handling
- assumption capture and propagation
- display-layer translation
- recoverable failure payloads
- workflow and end-to-end tests for intake and state flow

### Out of Scope

- changing the persona research strategy itself
- adding new persona segments
- adding retrieval/citation/RAG
- redesigning the HTML report visual system beyond exposing new brief/assumption sections

## Task Types

The system supports four business task types:

- `concept_test`
- `copy_feedback`
- `ab_test`
- `price_test`

### Routing Rules

The routing order is fixed:

1. `ab_test`
   Trigger only when the user clearly provides or references two or more versions, or explicit comparison language such as “A/B”, “哪版更好”, “版本1/版本2”.

2. `price_test`
   Trigger only when the user clearly asks about price acceptance, price band, pricing sensitivity, or promo-vs-regular pricing.

3. `copy_feedback`
   Trigger only when the user clearly provides at least one testable wording candidate or explicitly asks to evaluate copy lines, titles, ad text, or detail-page wording.

4. `concept_test`
   Default catch-all. Product concept, selling points, pack info, usage scenes, and target audience stay here unless stronger signals exist.

Hard rule:

- selling points are not copy by default
- selling points only become `copy_feedback` input when they are explicitly framed as wording to evaluate

## BusinessBrief

`BusinessBrief` is the only business-task intermediate object.

```python
@dataclass
class BusinessBrief:
    session_id: str
    raw_user_messages: list[str]
    attachments: list[str]
    task_type: str
    effective_task_type: str
    research_goal: str
    structured_facts: dict[str, Any]
    product_context: str
    copy_candidates: list[str]
    price_context: dict[str, Any]
    comparison_context: dict[str, Any]
    target_persona_hint: str
    missing_information: list[str]
    assumptions: list[str]
    degrade_history: list[str]
    execution_authorized: bool
    user_facing_status: str
```

### `structured_facts`

At minimum, store:

- `brand`
- `product_name`
- `product_form`
- `spec`
- `flavor`
- `target_age`
- `channel`
- `price`
- `selling_points`
- `usage_scenarios`
- `audience_hint`
- `competitor_reference`

### Field Semantics

- `task_type`: first-pass normalized task type
- `effective_task_type`: actual execution type after readiness evaluation and downgrade
- `research_goal`: one normalized business question
- `product_context`: concise product/concept summary for planner/agents
- `copy_candidates`: explicit wording candidates; used for copy and A/B tasks
- `price_context`: normalized price facts
- `comparison_context`: version mapping and comparison goal
- `missing_information`: current gate-level blockers
- `assumptions`: explicit assumptions used to execute under incomplete information
- `degrade_history`: internal downgrade chain such as `copy_feedback -> concept_test`
- `execution_authorized`: whether user language authorizes execution now

## UserMessagePresenter

`UserMessagePresenter` is the only component allowed to produce business-facing DingTalk messages.

### Responsibilities

- translate internal task/state/recovery objects into business Chinese
- explain downgrade and assumption execution explicitly
- render readiness, running, completion, and recovery messages
- prevent internal enum values and technical error strings from leaking

### Non-Responsibilities

- no parsing
- no readiness decisions
- no planner logic
- no state transitions
- no report generation

### Interface

```python
class UserMessagePresenter:
    def present_intake(self, brief: BusinessBrief) -> str: ...
    def present_readiness(self, brief: BusinessBrief, decision: ReadinessDecision) -> str: ...
    def present_dispatch_started(self, brief: BusinessBrief, decision: ReadinessDecision) -> str: ...
    def present_completed(self, brief: BusinessBrief, report: dict[str, Any]) -> str: ...
    def present_recovery(self, brief: BusinessBrief, payload: RecoveryPayload) -> str: ...
```

### Forbidden Direct User-Facing Terms

These must not appear in DingTalk replies:

- `copy_feedback`
- `concept_test`
- `P0`
- `P1`
- `missing_information`
- `awaiting_clarification`
- `fallback`
- `planner blocked`

### User-Facing Task Labels

- `concept_test -> 概念测试`
- `copy_feedback -> 文案测试`
- `ab_test -> 版本对比测试`
- `price_test -> 价格测试`

### User-Facing Status Labels

- `collecting -> 我在整理你刚刚提供的信息`
- `awaiting_authorization -> 信息已够我先跑一版，回复“先按当前信息跑一次”即可开始`
- `awaiting_clarification -> 还差少量关键信息，我先列给你`
- `running -> 我已经开始调研，接下来会汇总 8 类妈妈的反馈`
- `error -> 这次没有完整跑完，我把原因和下一步补给你`

## ReadinessGate

`ReadinessGate` is the only component allowed to decide whether the workflow can execute.

Output object:

```python
@dataclass
class ReadinessDecision:
    ready_to_run: bool
    effective_task_type: str
    missing_information: list[str]
    assumptions: list[str]
    degrade_history: list[str]
    execution_authorized: bool
    awaiting_status: str
    rationale: str
```

### Minimum Executable Conditions

#### `concept_test`

Requires:

- `research_goal`
- `product_context`, or enough structured facts to form one

If missing:

- ask follow-up questions

#### `copy_feedback`

Requires:

- `research_goal`
- at least one `copy_candidate`
- `product_context`

If missing copy but product concept exists:

- downgrade to `concept_test`

#### `ab_test`

Requires:

- `research_goal`
- at least two `copy_candidates` or two explicit concept versions
- `comparison_context`
- `product_context`

If only one version exists:

- downgrade to `copy_feedback`

If even copy feedback is under-specified but concept exists:

- downgrade to `concept_test`

#### `price_test`

Requires:

- `research_goal`
- `price_context`
- `product_context`

If price info is missing but concept exists:

- downgrade to `concept_test`

### Authorization Normalization

The following all map to `execution_authorized = true`:

- `先按当前信息跑一次`
- `先跑`
- `按假设做`
- `先看一版`

### Assumption Mode

When the user authorizes execution under assumptions:

1. assumptions are written to `BusinessBrief.assumptions`
2. `ReadinessGate` includes them in `ReadinessDecision`
3. planner consumes them
4. final report or execution note exposes them as execution boundaries

### Downgrade Rules

Downgrade is allowed only toward a less strict business question:

- `ab_test -> copy_feedback -> concept_test`
- `copy_feedback -> concept_test`
- `price_test -> concept_test`

Downgrade must:

- update `effective_task_type`
- append to `degrade_history`
- generate a user-facing explanation through `UserMessagePresenter`

## Six-Stage Workflow

### 1. Intake

Input:

- DingTalk message text
- attachments
- conversation context

Output:

- accumulated raw session context

### 2. Normalize

Input:

- raw session context

Output:

- `BusinessBrief`

Responsibilities:

- normalize task type
- extract business facts
- normalize research goal
- collect candidate copy, price, comparison, and scenario signals
- normalize execution authorization language

### 3. ReadinessGate

Input:

- `BusinessBrief`

Output:

- `ReadinessDecision`

Responsibilities:

- validate minimum fields by task type
- decide downgrade
- add assumptions
- decide whether to wait for authorization or clarification

### 4. Planner

Input:

- `BusinessBrief`
- `ReadinessDecision`

Output:

- `research_plan`

Responsibilities:

- decompose the business problem
- define research objectives, dimensions, and persona questions
- operate only on business brief, not legacy technical fields

### 5. Dispatch

Input:

- `BusinessBrief`
- `research_plan`

Output:

- mom-agent outputs
- synthesis output
- persisted report

Responsibilities:

- run mother agents
- synthesize findings
- preserve assumptions and downgrade boundary in output

### 6. Recovery

Input:

- failed stage context
- `BusinessBrief`

Output:

- `RecoveryPayload`
- business-facing recovery message

Responsibilities:

- classify failure stage
- preserve known information
- provide recoverable next actions

## State Transition Table

| Current Stage | Condition | Next Stage | Notes |
|---|---|---|---|
| `Intake` | new message accepted | `Normalize` | always |
| `Normalize` | brief built | `ReadinessGate` | always |
| `ReadinessGate` | not ready, clarification needed | `awaiting_clarification` | presenter explains missing items |
| `ReadinessGate` | ready but not authorized | `awaiting_authorization` | presenter asks for explicit go-ahead |
| `ReadinessGate` | ready and authorized | `Planner` | assumptions and downgrade locked |
| `Planner` | success | `Dispatch` | planner consumes `BusinessBrief` |
| `Planner` | failure | `Recovery` | returns structured recovery |
| `Dispatch` | success | `completed` | presenter returns business summary |
| `Dispatch` | mother agent failure | `Recovery` | no generic retry-only text |
| `Dispatch` | synthesizer failure | `Recovery` | no generic retry-only text |
| `Recovery` | user provides needed reply | `Normalize` | same session continues |

Hard rule:

- no node other than `ReadinessGate` may independently decide minimum runnable readiness

## RecoveryPayload

```python
@dataclass
class RecoveryPayload:
    failed_stage: str
    failure_reason: str
    preserved_information: list[str]
    missing_or_broken_items: list[str]
    recoverable_next_actions: list[str]
    suggested_reply: str
    user_message: str
```

### Business-Facing Failure Format

Every recovery message uses four parts:

1. where it got stuck
2. why it got stuck
3. what information has been preserved
4. what the user can reply next to recover

Example:

- 这次卡在调研汇总阶段。
- 原因是其中一类妈妈反馈没有完整返回，所以这版结果不能直接发给你。
- 我已经保留了产品名、卖点、规格、价格和使用场景。
- 你回复“继续重试当前任务”即可重新执行；如果要补信息，也可以直接补新的卖点或版本文案。

## Report Changes

Final report must preserve execution boundaries:

- `business_brief`
- `effective_task_type`
- `assumptions`
- `degrade_history`
- `research_plan`
- `structured_recommendation`

This ensures business users and auditors can see what was assumed and what mode actually ran.

## Testing Strategy

Testing focus moves from isolated runner validation to end-to-end intake and state flow.

### A. Task Recognition

- concept + selling points defaults to `concept_test`
- explicit testable copy line routes to `copy_feedback`
- two versions route to `ab_test`
- explicit pricing acceptance routes to `price_test`

### B. Information Extraction

Verify natural-language extraction of:

- brand
- product name
- spec
- flavor
- target age
- channel
- price
- selling points
- usage scenarios

Existing provided facts must not collapse into only product name.

### C. ReadinessGate

- validate minimum field sets per task type
- verify downgrade chains
- verify no node bypasses gate logic

### D. Authorization Normalization

Verify all supported authorization variants map to `execution_authorized = true`.

### E. Assumption Mode

- assumptions persist in `BusinessBrief`
- planner input includes assumptions
- final report or execution note exposes assumptions

### F. Recovery

- planner failure returns structured recovery
- mother agent failure returns structured recovery
- synthesizer failure returns structured recovery

### G. Presenter

- no internal terms leak into user messages
- downgrade explanation is explicit and business-readable
- recovery message is business-readable and actionable

## Implementation Notes

The current `TaskSessionManager` should not be patched incrementally around the legacy `mode/question_type/persona_id` flow. Instead:

- introduce new brief/gate/presenter modules
- adapt session persistence to store `BusinessBrief`
- rewire workflow nodes around the six-stage state machine
- migrate tests to the new intake path first

This is intentionally a structural refactor, not a regex patch.
