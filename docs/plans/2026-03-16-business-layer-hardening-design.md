# Business Layer Hardening Design

**Problem**

The DingTalk research workflow is now contract-stable at the infrastructure layer, but several business behaviors still drift:

- `price_test` and `ab_test` are not reachable through normal intake
- `purchase_decision` is collapsed into `product_concept` during `BusinessBrief` projection
- follow-up adjudication exists as a helper but is not connected to the main workflow
- explicit user requests for `single` mode and a specific persona are still planner suggestions instead of hard constraints

**Design**

We will harden the business layer in one slice so these rules stay consistent from intake to report:

1. Intake and `BusinessBrief` preservation
   - Extend session field collection to support `price_test` and `ab_test` inputs.
   - Preserve `purchase_decision`, `price_test`, and `ab_test` as first-class business task types through `BusinessBrief` and runner payload projection.
   - Parse price-specific fields into `BusinessBrief` so `ReadinessGate` can judge them in code instead of implicitly dropping them.

2. Follow-up arbitration at workflow ingress
   - Before mutating a completed session with new user text, run rule-first follow-up adjudication.
   - If the new message is `unrelated`, clear prior task business state and start a fresh intake so previous summary context cannot pollute the next task.
   - If the new message is same-topic, preserve a typed relation marker and prior snapshot reference instead of carrying over raw summary text as an uncontrolled prompt hint.

3. Explicit user-scope enforcement
   - Treat `single + persona_id` as a backend-enforced constraint.
   - Validate or normalize the planner result so a user-requested single persona cannot be widened into multi-persona fan-out by planner output drift.

**Data Flow**

- DingTalk event -> optional follow-up arbitration -> field extraction -> `BusinessBrief` -> `ReadinessGate` -> planner -> validated/normalized plan -> personas -> RA -> renderer

The critical rule is that business semantics are decided in typed backend code, not re-inferred later from prompt text.

**Error Handling**

- Invalid price-test combinations stay blocked in `ReadinessGate`.
- `unrelated` follow-ups clear prior task context before new extraction.
- Planner scope mismatches against explicit single-persona user input raise a structured validation failure or are normalized before dispatch.

**Testing**

We will add regression tests for:

- `purchase_decision` surviving `BusinessBrief` round-trip
- normal intake producing `price_test` and `ab_test` payloads
- completed-session unrelated follow-up starting a fresh intake without prior summary contamination
- explicit single-persona user requests surviving planner output drift
