# Persona Generation Constraints Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor persona generation so all 200 personas follow segment-level constrained randomness instead of global random behavior fields.

**Architecture:** Keep the current generator and output schema, but replace global sampling for mindset, need, channel, and behavior fields with rule-driven constrained sampling sourced from `persona_generation_rules(1).yaml`. Preserve subtype-driven language and decision logic while tightening mother-segment boundaries.

**Tech Stack:** Python, unittest, PyYAML, JSON

---

### Task 1: Add Failing Constraint Tests

**Files:**
- Create: `tests/test_generate_personas_constraints.py`
- Test: `tests/test_generate_personas_constraints.py`

**Step 1: Write the failing test**

Add tests that:
- load `generate_personas(1).py` by path
- load `persona_generation_rules(1).yaml`
- generate all personas with a fixed random seed
- assert generated core needs, channels, and behavior fields come from segment-specific options
- assert ordinal mindset fields remain within one step of the segment center value
- assert hard demographic and subtype constraints still hold

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_generate_personas_constraints -v`

Expected: FAIL because current generation uses global random pools for key fields.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 2: Refactor Generator to Use Layered Constraints

**Files:**
- Modify: `generate_personas(1).py`

**Step 1: Write minimal implementation**

Refactor the generator to:
- load segment rules from `persona_generation_rules(1).yaml`
- add helpers for ordinal constrained sampling
- sample needs/channels/behavior values only from the active segment whitelist
- sample mindset and switching willingness around the segment center with bounded variation
- preserve existing subtype-specific fields

**Step 2: Run tests to verify behavior**

Run: `python -m unittest tests.test_generate_personas_constraints -v`

Expected: PASS.

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 3: Regenerate Persona Outputs

**Files:**
- Modify: `persona_samples_complete.json`
- Modify: `persona_report.json`

**Step 1: Regenerate outputs**

Run the generator after the fix and overwrite the generated persona artifacts with the corrected outputs.

**Step 2: Verify regenerated structure**

Run a quick script to confirm:
- 200 samples exist
- 8 segments x 25 samples remain
- required top-level fields remain intact

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 4: Re-run Consistency and Diversity Validation

**Files:**
- Modify: `consistency_check_report(1).json`
- Modify: `diversity_check_report.json`

**Step 1: Run validation**

Run:
- consistency checker
- diversity checker

or equivalent wrapper scripts if module naming requires path-based imports.

**Step 2: Verify outcomes**

Confirm:
- consistency improves materially versus the previous `0.55` average
- diversity remains acceptable and warnings stay low

**Step 3: Commit**

Skip commit because this workspace is not a git repository.

### Task 5: Final Sanity Verification

**Files:**
- Review only: `generate_personas(1).py`
- Review only: `tests/test_generate_personas_constraints.py`
- Review only: generated JSON outputs

**Step 1: Run final verification**

Run:
- `python -m unittest tests.test_generate_personas_constraints -v`
- a fresh consistency/diversity verification command

**Step 2: Summarize final state**

Report:
- what changed
- the new validation numbers
- any residual rule conflicts that remain

**Step 3: Commit**

Skip commit because this workspace is not a git repository.
