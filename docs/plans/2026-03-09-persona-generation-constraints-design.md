# Persona Generation Constraints Design

**Date:** 2026-03-09

**Problem**

The current persona generator enforces demographic fields and subtype labels, but it randomizes core mindset, needs, channels, and behavior fields from global pools. This creates high diversity with weak segment boundary control, which breaks the intended "constrained randomness" model.

**Goal**

Make generated personas follow a layered constraint model:
- Mother segment defines the boundary.
- Subtype defines decision logic and expression style.
- Individual variation is allowed only within controlled bounds.

**Constraints**

- Keep the existing 8 segments x 25 samples structure.
- Preserve current subtype distribution per segment.
- Preserve current demographic realism and subtype-specific language fields.
- Use `persona_generation_rules(1).yaml` as the source of segment-level behavioral constraints.
- Do not require external services or a full app refactor.

**Design**

1. Segment rules become the source of truth for constrained fields.
   Segment-level mindset center values, need options, preferred channels, content habits, decision styles, family roles, and switching willingness will come from `persona_generation_rules(1).yaml`.

2. Generation uses a layered constraint model.
   Hard-constrained fields:
   - age, city, district, occupation, income, family structure, child age
   - subtype assignment
   - subtype-specific decision mode, trust trigger, rejection trigger, tone, quote, review focus

   Constrained-random fields:
   - openness level
   - time investment
   - appearance sensitivity
   - evidence sensitivity
   - trend sensitivity
   - price sensitivity
   - switching willingness

   These fields will use a center value from the segment rule plus bounded variation within adjacent ordinal levels only.

3. Segment-whitelist sampling replaces global pool sampling.
   The following will only be sampled from the active segment's allowed options:
   - core needs
   - preferred channels
   - content habit
   - decision style
   - family role

4. Output shape stays stable.
   Existing JSON structure and report files remain compatible so downstream scripts can continue reading generated personas.

**Testing**

- Add automated tests for:
  - segment whitelist compliance
  - bounded mindset variation
  - preserved hard demographic and subtype constraints
- Regenerate personas and rerun consistency and diversity checks.
- Success means consistency improves materially without collapsing diversity.

**Risks**

- Over-constraining can reduce variety too much.
- Segment rules and subtype rules may still disagree in a few places.
- Existing reports may change after regeneration; that is expected because the underlying personas are being corrected.
