# Development Plan – Media Promo Localizer

**Location:** `artifacts/DevPlan.md`  
**Audience:** Human developers and AI coding assistants (e.g., Claude, ChatGPT)

This document defines the **high-level development plan** for the Media Promo Localizer PoC, broken into small, concrete milestones (“sprints”) that can be executed largely by an AI assistant with human review.

It complements:

- `artifacts/FuncTechSpec.md` – behavioral specification
- `artifacts/CodingStandards.md` – code style and structure
- `artifacts/DevProcess.md` – collaboration and workflow rules

The goal is to give Claude clear objectives and a checklist so it can work in **batches** with minimal micro-management.

---

## 0. Milestone Overview

We’ll use small, incremental milestones:

- **Sprint 0 (done):** Repo bootstrap and control artifacts
- **Sprint 1:** Frontend shell + fake backend contract
- **Sprint 2:** Backend API service + end-to-end with stubbed pipeline
- **Sprint 3:** First real pipeline path (OCR + translation + inpainting, narrow scope)

The PoC is considered “demo-ready” once Sprints 1 and 2 are complete and stable. Sprint 3 is stretch / enhancement for extra impressiveness.

---

## 1. Sprint 0 – Bootstrap & Artifacts (Completed)

**Goal:** Create a clean, senior-looking repo with scaffolding and control docs to guide AI development.

**Key outcomes:**

- Repo `media-promo-localizer` created from the template.
- Husky + Conventional Commits confirmed working.
- `artifacts/FuncTechSpec.md` added and reviewed.
- `artifacts/CodingStandards.md` added and reviewed.
- `artifacts/DevProcess.md` added and reviewed.
- This `artifacts/DevPlan.md` and `artifacts/DevProgress.md` established as process artifacts.

**Status:** Done. No further AI work needed for this sprint unless docs change.

---

## 2. Sprint 1 – Frontend Shell + Fake/Stub Backend Contract

**Goal:** A working web UI that feels like a real app, wired to a **fake** translate-poster API, ready for demo with static or stub data.

### 2.1 Objectives

- Implement a simple **Login page**:
  - Email + password fields (no real auth; any values are accepted).
  - On “login”, set a basic in-memory “logged in” flag and navigate to the main app.
- Implement **Poster Localizer page**:
  - Upload control for a poster image (client-side only at this stage).
  - Language dropdown with options: `French, Spanish, German, Japanese, Korean`.
  - “Localize Poster” button.
  - Processing UX:
    - Animated indicator (spinner or progress bar).
    - Stage messages (e.g., “Analyzing text…”, “Translating…”, “Rendering localized poster…”).
- Define and implement **frontend types** for `POST /api/translate-poster` request/response matching the spec, including `timings` structure.
- Implement an **API client hook/module** that currently calls a **fake endpoint** or returns **hard-coded stubbed data**.
- Display a **sample localized poster image** in the UI (placeholder image from `/public` or similar) and show `timings` in a small “Performance details” panel.
- Add smoke tests for:
  - Login page renders and navigates.
  - Poster Localizer page renders core elements (upload, language select, button).
  - When “Localize” is clicked and the fake API resolves, the localized image + performance panel are shown.

### 2.2 Suggested Claude Tasks

You can give Claude a single batch task like:

> Implement Sprint 1 for the `media-promo-localizer` repo: login flow, Poster Localizer page with stubbed translate API, and basic tests, following FuncTechSpec, CodingStandards, DevProcess, and DevPlan in `artifacts/`. Operate in IMPLEMENTATION_MODE.

Internally, Claude should:

1. **Plan & list files to touch** under `apps/web/src` (pages, components, hooks, tests).
2. Implement Login + routing.
3. Implement Poster Localizer page UI, state, and processing UX.
4. Implement a stub `useTranslatePoster` or similar API hook returning fake data.
5. Add minimal tests.
6. Update `README` if needed to mention the main user flow.
7. Summarize files changed and how to run the app/tests.

### 2.3 Definition of Done

- `pnpm build` and `pnpm test` succeed.
- Login → main screen flow works in browser via `pnpm dev`.
- Selecting a sample image and language triggers a visible processing state and a final “localized result” view using stub data.
- Code adheres to Coding Standards (TS types, components, file naming).

---

## 3. Sprint 2 – Backend API + End-to-End with Stubbed Pipeline

**Goal:** Introduce a real backend service (e.g., FastAPI on Railway) that the frontend calls for `/api/translate-poster`, still using a stubbed pipeline that doesn’t yet invoke real OCR/translation/inpainting.

### 3.1 Objectives

- Create a backend Python service with:
  - FastAPI app entrypoint (e.g., `main.py`).
  - `GET /health` endpoint returning a simple JSON `{ "status": "ok" }`.
  - `POST /api/translate-poster` endpoint with:
    - Multipart image upload.
    - JSON fields for `source_language` and `target_language` (or just `target_language` if inferring source).
    - Response JSON matching the FuncTechSpec, including `localized_image_url` (or base64 image) and `timings` structure.
- Implement a **stub pipeline**:
  - No real OCR/translation/inpainting yet.
  - For now, return the original image or a placeholder localized image plus mock timings (e.g., ~300–500ms per step).
- Add basic backend tests (pytest):
  - `/health` returns 200 + expected JSON shape.
  - `/api/translate-poster` accepts a valid request and returns expected response fields.
- Wire the frontend to call the **real backend endpoint** instead of stubbed client-side fake:
  - Move API URL to env config (e.g., `VITE_API_BASE_URL` for frontend).
  - Handle failure cases in the UI (show friendly error messages).
- Prepare simple Railway deployment config for the backend (Dockerfile or Procfile-style as appropriate for the chosen stack).

### 3.2 Suggested Claude Tasks

Likely two batches:

1. **Backend batch (IMPLEMENTATION_MODE)**
   - Create backend package structure (`poster_localizer/api`, `poster_localizer/pipeline`, `poster_localizer/models`, etc.).
   - Implement endpoints + stub pipeline.
   - Add tests and a simple `README` section for running backend locally.

2. **Frontend integration batch (IMPLEMENTATION_MODE)**
   - Update API client to call Railway/localhost backend.
   - Ensure env-var-based configuration for API URL.
   - Refine error and loading states based on real network behavior.

### 3.3 Definition of Done

- Backend:
  - Can run locally (e.g., `uvicorn main:app --reload`).
  - Tests pass via `pytest` (or configured test command).
- Frontend:
  - Calls real `/api/translate-poster` endpoint.
  - Shows errors gracefully when backend is unavailable or returns 4xx/5xx.
- End-to-end demo:
  - You can run backend locally + frontend locally.
  - Upload a poster and see a localized result from the real backend stub.

---

## 4. Sprint 3 – First Real Pipeline Path (Narrow but Real)

**Goal:** Replace the stub pipeline with a **minimal, working pipeline** on a constrained subset of posters (horizontal English text only), so execs see genuine OCR/translation/inpainting in action.

### 4.1 Objectives

- Implement **OCR integration** for English-language text:
  - Pick one provider (cloud OCR or open-source) and implement it behind `IOcrClient`.
  - Extract detected text, positions, and approximate font/style hints if available.
- Implement **LLM-based translation**:
  - Integrate OpenAI or another LLM provider via `ITranslationClient`.
  - Send an array of text blocks + role tags (title, tagline, credits, etc.) in a single call where possible.
  - Ensure rules for not translating proper names (credits) are applied based on role tags.
- Implement **inpainting** for text regions:
  - Integrate LaMa or similar as `IInpaintingClient`.
  - For v0.1, inpaint the bounding boxes of original text to reconstruct background before placing translated text.
- Implement **text rendering**:
  - Use font approximation logic (per spec) to pick reasonable fonts for target languages.
  - For now, limit to horizontal text and visually similar fonts; no arcs or vertical stacks.
- Update timings:
  - Measure OCR, translation, inpainting, and rendering durations and return in `timings` as real values.
- Add tests for:
  - Role classification logic for text blocks.
  - Prompt building for translation client.
  - Pipeline behavior with mocked clients (happy path).

### 4.2 Suggested Claude Tasks

This sprint is more complex; break into several IMPLEMENTATION_MODE tasks:

1. Add `IOcrClient` and one concrete implementation + tests.
2. Add `ITranslationClient` + prompt builder + tests for mapping blocks.
3. Add `IInpaintingClient` integration + tests with mocked image calls.
4. Implement `PipelineContext` and main pipeline orchestrator, wiring all steps.
5. Update the API endpoint to call the real pipeline instead of stub.
6. Adjust frontend display to show richer timing info and any additional metadata if exposed.

### 4.3 Definition of Done

- Pipeline can process a small set of curated posters (horizontal English text) and produce visibly localized results for at least 2 languages (e.g., French, Spanish).
- `timings` reflects real step durations.
- Tests cover key pipeline logic and client interfaces.

---

## 5. Using DevProgress.md

Alongside this DevPlan, maintain a **progress log** in `artifacts/DevProgress.md`.

- After each significant Claude batch or manual coding session:
  - Append a new entry with date, sprint, mode, summary, files touched, tests run, and outcome.
- Claude is allowed to append entries to `DevProgress.md` when instructed, but should never rewrite history.

The combination of:

- `DevPlan.md` (roadmap) and
- `DevProgress.md` (journal)

will help Claude avoid “forgetting where it is” and give human reviewers a fast way to see what’s been done.

---

## 6. Adjustments

This plan is intentionally lightweight. As we learn how Claude behaves on this repo, we can:

- Split sprints further if needed.
- Move parts of Sprint 3 earlier or later.
- Add new milestones (e.g., multi-poster batching, project-level queue, or PSD export).

For now, these three sprints are sufficient to reach a powerful, **demo-ready PoC** that showcases real value to studio stakeholders.
