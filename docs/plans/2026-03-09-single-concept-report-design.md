# Single Concept Report Design

**Date:** 2026-03-09

**Problem**

The current workspace has a usable persona engine and orchestrator, but it does not provide a business-facing "single concept full report" workflow. Market teams still need a standard input contract, a fixed execution flow, and a report format they can read directly.

**Goal**

Add a first usable concept-testing layer that:
- accepts one standardized concept input
- runs all 200 personas through the existing orchestrator
- adds representative discussion and deep-dive interviews
- outputs a reusable JSON report plus a business-readable Markdown report

**Constraints**

- Reuse the existing persona base and `AgentOrchestrator`.
- Do not require a live LLM API for version one.
- Keep the first version focused on one concept only.
- Preserve room to extend later into A/B testing, packaging tests, and price ladders.
- Work within the current non-package Python workspace, including legacy filenames such as `digital_consumer_agents(1).py`.

**Design**

1. Add a separate concept-testing module rather than expanding the existing orchestrator file.
   The new module will own the market-testing workflow and business report structure, while `digital_consumer_agents(1).py` keeps its role as the persona execution engine.

2. Introduce a standard concept input object.
   The first version will accept:
   - `concept_name`
   - `brand`
   - `category`
   - `price`
   - `core_claims`
   - `packaging_summary`
   - `tagline`
   - `target_channels`
   - `competitive_anchors`
   - `context_notes`

   These fields will be mapped into the existing `Product` object plus an auxiliary context block for reporting.

3. Fix the execution flow to four stages.
   - Full batch evaluation across 200 personas
   - Representative discussion with one participant per mother segment where possible
   - Deep-dive interviews covering high-intent, hesitant, and rejecting personas
   - Report synthesis into business-readable sections

4. Generate a stable business report shape.
   The report will contain:
   - `executive_summary`
   - `purchase_intent`
   - `segment_opportunity`
   - `reasons_to_buy`
   - `barriers`
   - `voice_of_consumer`
   - `optimization_suggestions`
   - `appendix`

5. Output both machine-readable and business-readable artifacts.
   - JSON for reuse by downstream tooling
   - Markdown for direct reading by market and brand teams

**Execution Rules**

- Discussion participants should prioritize segment coverage before extreme sampling.
- Deep-dive interviews should default to `2 high intent + 2 hesitant + 2 rejecting`.
- Consumer voice excerpts should be capped so the report stays readable.
- First version will use the current template-style response generation and evaluation heuristics.

**Testing**

- Add tests for the concept input to product mapping.
- Add tests for end-to-end report generation against the 200-persona dataset.
- Add tests for report structure, segment coverage, deep-dive bucket selection, and Markdown rendering.
- Run the new tests plus the existing persona constraint tests.

**Risks**

- Existing evaluation heuristics are still rule-based and may understate nuance.
- Template-style response generation can produce repetitive language in the report.
- Dynamic loading is required because the current engine file uses a legacy filename.

**Non-Goals for Version One**

- No A/B comparison
- No price ladder simulation
- No packaging image understanding
- No external LLM integration
