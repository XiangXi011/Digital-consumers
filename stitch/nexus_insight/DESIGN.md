# Design System Document: The Precision Architect

## 1. Overview & Creative North Star
The "Precision Architect" is the guiding philosophy of this design system. In the world of AI market research, data is often chaotic. Our role is to act as the "Digital Curator," transforming raw information into a structured, editorial experience that feels authoritative yet effortless.

This system moves beyond the "Standard SaaS" look by rejecting rigid, boxy layouts in favor of **Tonal Architecture**. We utilize intentional asymmetry, varying typographic scales, and layered surfaces to guide the eye. Instead of a flat grid, we treat the dashboard as a high-end physical workspace—clean, expansive, and thoughtfully curated.

**Creative North Star: The Digital Curator**
*   **Intentionality over Density:** Use white space as a functional tool, not a "void."
*   **Depth over Lines:** Hierarchy is defined by light and elevation, never by strokes.
*   **Editorial Authority:** High-contrast typography transitions that mirror premium financial journals.

---

## 2. Colors: The Tonal Palette
We leverage a sophisticated spectrum of blues and neutrals to establish trust. The color strategy is built on "Surface-on-Surface" logic rather than "Object-on-Background."

### Core Palette
*   **Primary (`#003d9b`):** Use for high-intent actions and brand presence.
*   **Primary Container (`#0052cc`):** Use for subtle branding accents and active states.
*   **Surface / Background (`#f8f9fb`):** The foundational "canvas."

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders for sectioning or containment. 
Boundaries must be defined solely through background color shifts. For example:
*   A `surface-container-low` dashboard card sitting on a `surface` background.
*   A `surface-container-highest` sidebar juxtaposed against a `surface-container` main content area.

### Surface Hierarchy & Nesting
Treat the UI as layered sheets of frosted glass.
1.  **Base:** `surface` (#f8f9fb)
2.  **Level 1 (Sections):** `surface-container-low` (#f3f4f6)
3.  **Level 2 (Active Cards):** `surface-container-lowest` (#ffffff)
4.  **Level 3 (Popovers/Modals):** `surface-container-high` (#e7e8ea)

### The "Glass & Gradient" Rule
To elevate the AI-driven nature of the platform:
*   **CTAs:** Use a subtle linear gradient from `primary` (#003d9b) to `primary_container` (#0052cc) at a 135° angle. This adds "soul" and depth.
*   **Floating Navigation:** Apply `surface_container_lowest` with a 20px Backdrop Blur and 85% opacity to create a high-end glassmorphic effect for top headers or floating filter bars.

---

## 3. Typography: Editorial Hierarchy
We utilize a pairing of **Manrope** (for authoritative headlines) and **Inter** (for data precision).

*   **Display & Headline (Manrope):** Use for high-level insights and data summaries. The geometric nature of Manrope conveys a modern, tech-forward reliability.
    *   *Display-LG (3.5rem):* Reserved for hero metrics (e.g., "98% Sentiment").
*   **Title & Body (Inter):** The workhorse for data tables and detailed analysis. Inter’s high x-height ensures legibility in data-heavy environments.
    *   *Title-MD (1.125rem):* Used for card titles to provide a clear entry point.
    *   *Body-MD (0.875rem):* The standard for all dashboard content.
*   **Labels (Inter):** Used for micro-copy and chart legends.
    *   *Label-SM (0.6875rem):* Use Uppercase with +5% letter spacing for a premium, architectural feel.

---

## 4. Elevation & Depth: Tonal Layering
Traditional shadows are often "dirty." We use **Ambient Depth**.

### The Layering Principle
Hierarchy is achieved by stacking tiers. An AI insight card should be `surface-container-lowest` placed upon a `surface-container-low` background. This creates a natural, soft "lift."

### Ambient Shadows
When an element must float (e.g., a dropdown or a primary modal):
*   **Shadow Color:** Use a tinted version of `on-surface` (e.g., `#191c1e` at 6% opacity).
*   **Blur:** Extra-diffused (e.g., `0px 20px 40px`). This mimics soft, natural studio lighting rather than a harsh digital drop shadow.

### The "Ghost Border" Fallback
If accessibility requires a border (e.g., in high-contrast modes), use a **Ghost Border**:
*   Token: `outline-variant` (#c3c6d6)
*   Opacity: **15% max.** It should be felt, not seen.

---

## 5. Components: Refined Primitives

### Buttons
*   **Primary:** Gradient-filled (`primary` to `primary_container`), `xl` roundedness (0.75rem). No border.
*   **Secondary:** `surface-container-highest` background with `on-surface` text.
*   **Tertiary:** Ghost style; text only, using `primary_fixed_variant` for the label.

### Data Cards
*   **Styling:** Forbid divider lines. Use `spacing-6` (1.3rem) of vertical white space to separate the header from the content.
*   **Corner Radius:** Always use `xl` (0.75rem) for external cards and `md` (0.375rem) for internal nested elements to create a "nested container" visual logic.

### AI Insight Chips
*   **Selection:** Use `primary_fixed` (#dae2ff) background with `on_primary_fixed` (#001848) text. 
*   **Shape:** `full` roundedness (pill shape) to contrast against the structured grid.

### Sophisticated Charts
*   **Radar/Line Charts:** Use `surface_tint` (#0c56d0) for the primary data path. 
*   **Grid Lines:** Must be `outline_variant` at 10% opacity or removed entirely.
*   **Interaction:** Use a `surface-container-lowest` tooltip with a 4% ambient shadow.

### Input Fields
*   **State:** Default state uses `surface-container-highest` background. Focus state uses a 2px "Ghost Border" in `primary`.

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical spacing (e.g., wider margins on the left of a content block) to create an editorial, magazine-like flow.
*   **Do** use `tertiary` (#7b2600) sparingly to highlight critical AI "anomalies" or "outliers" in market data.
*   **Do** prioritize "Breathing Room." If a dashboard feels crowded, increase the spacing from `8` (1.75rem) to `10` (2.25rem) before removing content.

### Don't
*   **Don't** use 100% black text. Always use `on_surface` (#191c1e) to maintain a premium, soft-ink look.
*   **Don't** use "Alert Red" for everything. Use `error` (#ba1a1a) only for system failures; use `tertiary` for market data warnings to avoid "user fatigue."
*   **Don't** use hard-edged corners. Every element should have at least `sm` (0.125rem) roundedness to feel approachable.