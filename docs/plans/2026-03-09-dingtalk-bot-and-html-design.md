# DingTalk Bot And HTML Report Design

**Date:** 2026-03-09

**Problem**

The current workspace can generate single-concept, A/B, price ladder, and packaging review reports, but it still requires direct script execution. The desired workflow is conversational: users should be able to `@` a DingTalk bot in a group, provide product information, receive structured follow-up questions, and finally get a short summary plus a polished HTML report.

**Goal**

Add a DingTalk-facing workflow that:
- collects product information from group chat messages
- first lists the full information checklist
- then identifies missing fields and asks targeted follow-up questions
- asks whether to run on currently known information when the data is incomplete
- starts analysis after either full collection or explicit user confirmation
- outputs a short conclusion in chat plus a complete HTML report

**Constraints**

- Keep the first version file-based and local; no database required.
- Support asynchronous two-stage interaction:
  - acknowledge analysis start
  - return final result after generation
- Use the existing testing engine rather than re-implementing analysis logic.
- Reuse the user-provided HTML style direction.
- Allow incomplete execution only when the user explicitly authorizes it.

**Design**

1. Add a session manager.
   Create a file-backed session layer that stores:
   - group id
   - conversation id
   - user id
   - collected product fields
   - missing fields
   - whether incomplete execution has been authorized
   - current status
   - generated task/report paths

2. Add a DingTalk workflow service.
   The bot service should:
   - accept normalized DingTalk message payloads
   - detect whether the message starts a new task or continues an existing one
   - return the full checklist on first contact
   - parse provided product information from the message
   - ask only for missing fields after the checklist step
   - explicitly ask whether to run on partial data when applicable
   - create a pending analysis task when the user confirms

3. Add an HTML renderer.
   Create a dedicated renderer for complete reports using the supplied visual direction:
   - gradient hero header
   - KPI cards
   - segment ranking
   - insight cards
   - consumer quote cards
   - appendix / missing-information section

4. Keep execution decoupled.
   The DingTalk layer should not know report internals. It should call the concept-testing layer, get a report object, render HTML, and return a short summary plus output path metadata.

**Conversation Rules**

- First reply: always provide the full information checklist.
- After the user supplies information: summarize what is known and what is still missing.
- If anything important is missing: ask whether to continue with current information.
- If the user says "run with current info" or equivalent: proceed.
- If information is sufficient: proceed without further approval.

**Testing**

- Add tests for:
  - first-contact checklist response
  - partial-information follow-up behavior
  - explicit partial-run confirmation
  - completed analysis response with HTML output path
  - HTML renderer output structure

**Risks**

- Rule-based field extraction from free-form chat can miss ambiguous details.
- DingTalk callback structure may vary and will require adapter tuning during real integration.
- HTML file delivery details depend on the final DingTalk transport path.

**Non-Goals**

- No real DingTalk webhook deployment in this workspace
- No database or distributed task queue
- No OCR on arbitrary packaging text from uploaded documents
