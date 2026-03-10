# Advanced Testing And AI Design

**Date:** 2026-03-09

**Problem**

The current workspace now supports a first full single-concept report, but it still lacks the remaining product boundaries needed for a more complete market-testing toolkit:
- A/B comparison
- price ladder analysis
- packaging image understanding
- real LLM-enhanced language generation

**Goal**

Extend the testing system so it can:
- compare two concepts in one report
- evaluate one concept across multiple price points
- read a packaging image through a Vision-capable OpenAI-compatible API
- optionally replace template-style discussion, interview, and report language with real LLM outputs

**Constraints**

- Use an OpenAI-compatible interface rather than hard-coding one provider.
- Keep graceful degradation when no API configuration exists.
- Do not replace the rule-based scoring engine with an LLM.
- Reuse the current persona engine and concept-testing workflow where possible.
- Keep the first implementation file-based and script-driven; no web app or database.

**Design**

1. Add an AI adapter layer.
   Create a dedicated client module that:
   - reads environment variables for API access
   - supports chat completion for text generation
   - supports vision analysis for packaging image descriptions
   - exposes a small stable interface to the rest of the system
   - returns safe fallbacks when configuration is absent

2. Add an advanced testing orchestration layer.
   Create a second module above the existing single-concept runner that handles:
   - A/B comparison
   - price ladder testing
   - packaging review from images
   - optional LLM-enhanced rendering

3. Keep scoring and expression separate.
   - Existing rule-based scoring remains the source of quantitative outputs.
   - LLM usage is limited to language generation, explanation synthesis, and visual summarization.
   - Vision output becomes structured packaging context, not direct persona scoring.

4. Make every advanced capability runnable and degradable.
   - If API configuration exists, use real LLM / Vision calls.
   - If not, return deterministic local fallbacks.
   - Tests should prove both modes work.

**Feature Scope**

**A/B comparison**
- Run two concepts through the same persona base
- compare summary metrics, segment winners, key barriers, and recommendation

**Price ladder**
- Run one concept across multiple prices
- show per-price intention, conversion, and a recommended price zone

**Packaging vision review**
- Accept a local image path
- extract a structured packaging summary via Vision
- feed that summary into the existing concept-testing flow

**LLM-enhanced outputs**
- enhance discussion responses
- enhance deep-dive responses
- enhance report narration and conclusion text

**Testing**

- Add unit tests for:
  - OpenAI-compatible configuration and fallback behavior
  - A/B report structure and comparison logic
  - price ladder output shape and price-point ordering
  - packaging image review behavior with stubbed Vision client
  - optional LLM-enhanced text generation behavior

- Keep real API calls out of core tests.
- Real API usage should be optional and script-driven.

**Risks**

- Real API responses may vary; structured prompts need strict output contracts.
- Vision summaries can be noisy if packaging images are poor quality.
- Report language can drift if prompts are too loose.

**Non-Goals**

- No front-end UI
- No persistent database
- No multi-image packaging boards
- No long-memory autonomous agent behavior
