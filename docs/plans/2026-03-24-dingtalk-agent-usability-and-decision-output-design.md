# DingTalk Agent Usability And Decision Output Design

**Date:** 2026-03-24

## Problem

Colleague feedback points to two product failures:

1. intake is too strict, so feeding material into the agent feels like form-filling
2. output feels low-value because it summarizes instead of helping the business make a decision

The current system has four concrete causes:

- a new session sends the checklist before parsing the user's first real message, so complete first-turn inputs are effectively ignored
- field extraction is biased toward labeled template input
- image attachments are collected, but OCR / field extraction is not connected to the DingTalk intake path
- persona outputs are over-shaped by rubric scores, decision weights, and backend scoring, which makes different mothers sound like variants of the same rational reviewer

## Product Goal

Turn the DingTalk agent from a structured research collector into a low-friction decision assistant:

- users should be able to drop messy text, partial notes, and screenshots without carefully formatting them
- the 8 personas should react like different real consumers under incomplete information, with different emotional triggers and decision habits
- every completed run should produce a decision card that helps the business decide whether to push, revise, or pause

## Confirmed Decisions

- output should optimize for `可直接拍板的结论建议`
- incomplete information must not block a recommendation
- persona disagreement must not block a recommendation
- personas should decide by gut first, not by slow rational review
- the strongest persona differences should appear in this order:
  - emotional triggers
  - decision path
  - voice style
- model judgment should lead persona behavior; backend rules should be reduced to a small set of guardrails

## Design

### 1. Intake becomes tolerant by default

The first user message in a new session must be parsed immediately instead of being discarded behind a checklist response.

Intake should support three user behaviors equally well:

- semi-structured labeled input
- messy natural-language task descriptions
- screenshots / posters / detail-page images

It must also support the way business users actually brief products:

- pasted ecommerce links such as Taobao item links
- pasted product titles next to links
- a short list of selling points
- multiple question groups in one request
- personalized free-form questions mixed into the standard research prompts

Design changes:

- parse the first real message before deciding whether a checklist reminder is still necessary
- treat the checklist as a helper message, not as a gate
- keep field inference for `mode`, `question_type`, `persona_id`, and `user_question`, but reduce the expectation that users must label every field
- when attachments are present, run OCR / product-field extraction and merge the extracted signals into the session before readiness evaluation
- when information is still partial, continue with the best current brief instead of insisting on a complete research form
- preserve source links as first-class input context instead of dropping them as noise
- allow `product_info` to be assembled from mixed sources:
  - direct product description text
  - ecommerce link + visible title
  - OCR-extracted packaging / detail-page text
- allow `copy_material` to be a list of claims rather than one flat paragraph
- allow `user_question` to be represented internally as a question bundle instead of a single sentence when the user provides multiple sub-questions

Recommended intake interpretation:

- keep one primary task mode for orchestration
- allow one request to contain multiple question clusters such as:
  - product concept questions
  - purchase decision questions
  - copy / selling point questions
- preserve user-authored question wording whenever possible instead of rewriting everything into a fixed generic template
- treat personalized questions as valid research prompts, not as malformed input

### 2. Personas become instinctive instead of rubric-driven

The current persona layer overfits to rational evaluation because each persona is forced through common score dimensions, backend purchase scoring, and YAML decision weights.

The new persona layer should be model-led and reaction-first.

Each persona should process information in this order:

1. first impression
2. default action
3. post-hoc explanation
4. switch condition

Required persona output shape:

- `instant_feeling`
- `default_action`
- `gut_stance`
- `emotional_trigger`
- `posthoc_reasoning`
- `switch_condition`
- `verbatim_answer`

Persona behavior rules:

- personas are allowed to decide under incomplete information
- personas are allowed to be biased, impatient, emotional, lazy, trend-following, or risk-averse
- personas must not speak like strategists, consultants, or product reviewers
- personas should not be forced to score fixed dimensions before reacting

Persona asset changes:

- replace hard decision framing in YAML with soft behavioral guidance
- move from `decision_weights`, `veto_rules`, and `feature_scoring_rubric` toward:
  - `emotional_triggers`
  - `default_decision_path`
  - `low_info_heuristics`
  - `voice_style`

### 3. Decision output replaces summary output

The system should no longer optimize for a general research summary as the primary user-facing result.

The primary DingTalk output becomes a decision card with five blocks:

- `拍板建议`: `建议推进` / `建议修改后推进` / `建议暂缓`
- `一句话判断`
- `最影响决策的 3 条证据`
- `优先人群`
- `立即动作`

When the user asks multiple concrete questions, the decision card should still answer them in a usable way.

Recommended addition:

- `关键问题答复`: 3-5 short answers mapped to the user's most decision-relevant questions

Example:

- 这款产品有吸引力吗
- 最打动人的点是什么
- 最大顾虑是什么
- 是否愿意为变色功能多花钱
- 哪句文案最值得保留 / 重写

Decision behavior rules:

- every completed run must return one explicit recommendation
- incomplete information should be framed as `基于当前信息的最优判断`, not as a block
- disagreement should be translated into audience strategy, not vague indecision
- the system should still surface the biggest risk and the one most useful next validation action

Recommended internal structure:

- backend builds a light `decision_frame`
- synthesis LLM turns that frame plus persona evidence into a readable `decision_card`

This keeps the final output actionable without collapsing all reasoning into brittle hard-coded rules.

### 4. Preserve only the guardrails that protect system integrity

We should remove rules that force personas to behave like analysts, but keep rules that protect identity, traceability, and workflow safety.

Guardrails to keep:

- `persona_id` must remain stable
- outputs must stay structured enough for downstream rendering
- synthesized conclusions must remain traceable to persona evidence
- minority rejection reasons must be preserved
- `BusinessBrief`, authorization, follow-up arbitration, and session isolation remain backend-enforced

Guardrails to remove or weaken:

- mandatory persona rubric scoring
- backend purchase-intent math as the primary persona decision source
- shared evaluation-dimension framing inside each persona response
- rigid veto-style logic that makes all personas converge on cautious rationality

## Output Contract

The report should keep its current top-level JSON shape for compatibility, but the meaning of the payload should shift toward decision support.

Recommended additions:

- `decision_card`
- `decision_frame`
- `source_links`
- `custom_questions`

`decision_card` should include:

- `decision`
- `decision_rationale`
- `key_evidence`
- `priority_audiences`
- `major_risk`
- `immediate_action`
- `confidence_mode`
- `question_answers`

`custom_questions` should preserve user-authored question text in order, so synthesis can answer the user's actual wording rather than only the system's normalized categories.

`research_summary` and `structured_recommendation` can remain during migration, but should become secondary compatibility layers rather than the main product surface.

## UX Changes

### DingTalk

The completion message should stop being a single short summary sentence.

It should instead render:

- the recommendation
- one-line rationale
- top evidence
- audience priority
- immediate action
- report link if available

### HTML

The HTML report should become a decision memo rather than a research scrapbook.

Top-of-report sections:

1. decision
2. evidence
3. audience fit
4. immediate action

Consumer voice cards should still exist, but they should support the decision instead of dominating the page.

## Implementation Slices

1. Intake usability slice
   - parse first-turn messages
   - connect attachment OCR / extraction into session enrichment
   - reduce checklist gating

2. Persona realism slice
   - replace rubric-first persona prompting with instinct-first prompting
   - refactor persona validation schema
   - update persona YAML guidance

3. Decision output slice
   - add `decision_frame` and `decision_card`
   - rewrite DingTalk completion summary
   - redesign HTML report top section

4. Regression and migration slice
   - keep compatibility where needed for existing report consumers
   - update tests from summary presence checks to decision-card checks

## Testing

We should add or update tests for:

- first-turn message ingestion in new sessions
- attachment OCR enrichment being merged into intake
- persona outputs remaining identity-stable while using instinct-first fields
- multi-persona disagreement still producing an explicit recommendation
- incomplete information still producing an explicit recommendation
- DingTalk completion messages containing a decision card rather than only a short summary
- HTML report top section rendering the decision memo structure

## Non-Goals

- rebuilding the 8-persona taxonomy from scratch
- removing `BusinessBrief` or workflow hardening rules that protect session correctness
- turning the system into a free-form chat assistant with no structured output
