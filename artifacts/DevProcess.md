# Dev Process – Media Promo Localizer

> **Version History**
>
> - 2025‑12‑10 – v1.1 – Clarified how control docs, sprints, Cursor/Sonnet sessions, and DevProgress work together as a repeatable workflow.
> - 2025‑11‑xx – v1.0 – Initial version prior to control‑doc consolidation.

---

**Audience:** Human developers and AI coding assistants (e.g., Claude, ChatGPT)

This document defines **how work should be done** in this repo when using AI-assisted, spec-driven development.
It complements:

- `artifacts/FuncTechSpec.md` – what to build
- `artifacts/coding/CodingStandards.md` – how the code should look

The goal is to make AI assistants behave like a disciplined dev team, not a code firehose.

---

## 1. Core Principles

1. **Spec first**
   - Always treat `FuncTechSpec.md` as the **source of truth** for behavior.
   - If the spec is ambiguous, ask for clarification _before_ inventing behavior.

2. **Coding Standards second**
   - Follow `CodingStandards.md` for structure, naming, typing, and style.
   - If existing code deviates, prefer to follow the standards and clean as you go (within the scope of the task).

3. **Small, coherent changes**
   - Each change should be a small, reviewable unit:
     - A single feature slice
     - A small refactor
     - A narrow bugfix
   - Avoid large, repo-wide transformations unless explicitly requested.

4. **Human-readable first**
   - Code, tests, and comments should be understandable by a senior engineer skimming under time pressure.
   - Avoid cleverness where a simple approach suffices.

---

## 2. Modes of Operation (Change Safety Rule)

To prevent AI from “fixing” the wrong thing (e.g., changing tests to match buggy code), all work must operate under a **mode**. Only one mode may be active for a given task.

### 2.1 IMPLEMENTATION_MODE

Use when implementing new features or behavior.

Allowed:

- Add or modify **application code**.
- Add **new tests** that capture the intended behavior.

Forbidden:

- Modifying existing test expectations unless explicitly instructed.

If existing tests fail in this mode:

- Do **not** change the tests to make them pass.
- Instead, analyze whether:
  - The implementation is wrong, or
  - The spec has changed.
- Ask for clarification if there is any doubt.

### 2.2 TEST_REPAIR_MODE

Use when the specification is clear and tests are known to be wrong/outdated.

Allowed:

- Modify tests and expectations to correctly reflect the spec.
- Add new tests for missing edge cases.

Forbidden:

- Modifying application code.

If fixing tests reveals that code is incorrect:

- Do not “sneak” code changes into this mode.
- Finish updating the tests, then request an IMPLEMENTATION_MODE task for the corresponding code changes.

### 2.3 REFINEMENT_MODE

Use for small, well-scoped improvements agreed upon in advance.

Allowed:

- Minor refactors, comment improvements, small UX polish, etc.
- Only in the explicitly listed files.

Forbidden:

- Large changes across many files.
- Changing both code and tests in ways that affect behavior.

### 2.4 Mode Expectations for AI Assistants

When an AI assistant is asked to make changes, the prompt should state the mode explicitly, e.g.:

> “Operate in IMPLEMENTATION_MODE. You may modify application code and add new tests, but you may not change existing test expectations.”

If an AI assistant is unsure which mode applies, it must **ask**.

---

## 3. Task Workflow

Each task or request to an AI assistant should roughly follow this flow.

### 3.1 Preparation

1. Identify the task clearly:
   - Example: “Implement the stub Login page and gate access to the Poster Localizer page.”
2. Specify the **mode** (IMPLEMENTATION_MODE, TEST_REPAIR_MODE, or REFINEMENT_MODE).
3. Point the assistant at relevant artifacts:
   - `FuncTechSpec.md`
   - `CodingStandards.md`
   - Any relevant source files

### 3.2 AI Assistant Behavior (Per Task)

When Claude or another AI is asked to implement a task, it should:

1. **Restate the task** in its own words to confirm understanding.
2. **List the files** it intends to create/change (high-level plan).
3. **Outline the steps** it will take, in order.
4. Implement changes in **small increments**, keeping related logic together.
5. Update or add tests as allowed by the current mode.
6. Summarize:
   - Files changed
   - New components/endpoints
   - Any new types, models, or utilities
7. Note any open questions or follow-ups needed.

### 3.3 Human Review

After AI-generated changes:

1. Review the diff for:
   - Alignment with the spec
   - Compliance with Coding Standards
   - Unintended changes (e.g., touching unrelated files)
2. Run locally:
   - `pnpm lint` / `pnpm test` for frontend
   - Backend tests where applicable (`pytest`, etc.)
3. Only approve/keep changes that are coherent and spec-aligned.

---

## 4. Frontend-Specific Process

### 4.1 Typical Frontend Task

Example: “Add the stub Login page and wire it to the Poster Localizer page.”

Steps the AI should take:

1. Check `FuncTechSpec.md` → Section 9 (Frontend Requirements).
2. Confirm the routing approach used in `apps/web` (React Router, etc.).
3. Plan:
   - New `LoginPage` component
   - Updates to routing
   - State management for a simple “logged in” flag
4. Implement:
   - Use TypeScript types for props and any auth state.
   - Follow file naming conventions (PascalCase, etc.).
   - Add minimal tests verifying:
     - Login form renders
     - Successful “login” leads to Poster Localizer page
5. Ensure:
   - The app still builds and runs via `pnpm dev`.
   - No unrelated files are changed.

### 4.2 API Integration Tasks

When introducing or updating an API call from the frontend:

1. Centralize API calls in a dedicated module or hook.
2. Use typed request/response models that mirror the backend schemas.
3. Handle error states explicitly in the UI.
4. Do not hardcode URLs or secrets; use env vars (`VITE_API_BASE_URL`).

---

## 5. Backend-Specific Process

### 5.1 Typical Backend Task

Example: “Implement `POST /api/translate-poster` with a stubbed pipeline.”

Steps:

1. Read `FuncTechSpec.md` → Sections 5 and 6.
2. Design or confirm:
   - Location of FastAPI app (e.g., `poster_localizer/api/routes.py`).
   - Pydantic models for request/response.
   - `PipelineContext` structure and orchestrator skeleton.
3. Implement:
   - Endpoint handler with correct request/response models.
   - Stubbed pipeline that returns a dummy localized image URL and timings.
4. Add backend tests (pytest):
   - Endpoint returns 200 on valid input.
   - Response structure matches spec, including `timings`.

### 5.2 Using External Services (OCR, Translation, Inpainting)

When integrating real external services:

1. Implement provider clients behind interface-like classes (see Coding Standards).
2. Load configuration (API keys, URLs) from environment variables.
3. Handle failures gracefully and log helpful error messages.
4. Keep external integration localized to `clients/`, not scattered throughout the pipeline.

---

## 6. File & Scope Boundaries

To keep the repo coherent:

1. **Do not rename** core directories (e.g., `apps/web`) without explicit instruction.
2. **Do not modify**:
   - Husky config
   - CI workflows
   - Artifact files (spec, coding standards, process docs)
     unless the task is explicitly about updating them.
3. Limit changes to files directly relevant to the task.

If a change would naturally require touching many areas (e.g., a cross-cutting refactor), split it into smaller tasks and confirm with a human first.

---

## 7. Prompts & Interaction Patterns for Claude

When asking Claude to work in this repo, use prompts that:

1. **Specify the mode**, e.g.:
   - “Operate in IMPLEMENTATION_MODE for this task…”
2. **Provide context**:
   - Link or paste relevant sections of `FuncTechSpec.md` and `CodingStandards.md` (or summarize key points).
3. **Define the scope**:
   - List which parts of the app to touch (e.g., “only under `apps/web/src/pages` and `apps/web/src/components`”).

Example prompt structure:

> You are acting as a senior engineer working in the `media-promo-localizer` repo.
> Operate in IMPLEMENTATION_MODE: you may modify application code and add tests, but you may not modify existing test expectations.
> Your task: [clear description].
> Follow `FuncTechSpec.md` and `CodingStandards.md`.
> First, restate the task, then list the files you plan to touch, then implement.

This reduces confusion and keeps the assistant tightly aligned with project norms.

---

## 8. When to Ask for Clarification

AI assistants should **pause and ask** instead of guessing when:

1. The spec and existing code appear to conflict.
2. It is unclear whether a requirement is in scope for the current milestone.
3. Implementing the obvious solution would require introducing a new major dependency.
4. A change would impact multiple subsystems or require modifying tests and code together.

It is always better to ask one clarifying question than to implement a large, incorrect change.

---

## 9. Summary

- **Spec:** defines what to build.
- **Coding Standards:** define how it should look in code.
- **This Dev Process:** defines how humans and AI collaborate safely and predictably.

Follow these rails and the repo will look like it was built by a careful, senior-led team—even when AI is doing much of the typing.
