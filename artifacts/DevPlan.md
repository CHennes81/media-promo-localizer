# Development Plan – Media Promo Localizer

**Location:** `artifacts/DevPlan.md`
**Audience:** Human developers and AI coding assistants (e.g., Cursor, Claude, ChatGPT)

This document defines the **high-level development plan** for the Media Promo Localizer PoC, broken into small, concrete milestones (“sprints”) that can be executed largely by an AI assistant with human review.

It complements:

- `artifacts/spec/FuncTechSpec.md` – functional & technical specification (authoritative behavior and architecture)
- `artifacts/spec/API_Definition.md` – backend HTTP API contract (authoritative endpoints & payloads)
- `artifacts/DevChecklist_Sprint2.md` – detailed Sprint 2 backend checklist
- `artifacts/DevProgress.md` – running progress log and journal
- `artifacts/CodingStandards.md` – code style and structure (if present)
- `artifacts/DevProcess.md` – collaboration and workflow rules (if present)

The goal is to give AI coding assistants clear objectives and a stable roadmap, so they can work in **batches** with minimal micro-management and without drifting from the spec.

---

## 0. Milestone Overview

We are structuring the work into small, incremental sprints:

- **Sprint 0 (done):** Repo bootstrap, core artifacts, and process scaffolding
- **Sprint 1 (done):** Cinematic frontend shell with stubbed “localize poster” UX
- **Sprint 2 (current):** FastAPI backend service (`apps/api`) with async job model and mock localization pipeline
- **Sprint 3 (planned):** First live pipeline path (OCR + translation + inpainting) behind the same contract

The PoC is considered **demo-ready** once Sprints 1 and 2 are complete and stable. Sprint 3 is a stretch goal that adds real AI magic on a constrained subset of posters.

---

## 1. Sprint 0 – Bootstrap & Artifacts (Completed)

**Goal:** Create a clean, senior-looking repo with scaffolding and control docs to guide AI development.

**Key outcomes:**

- Repo `media-promo-localizer` created and initialized.
- Base project layout established:
  - `apps/web/` – React/Vite frontend
  - `apps/api/` – FastAPI backend (to be built in Sprint 2)
  - `artifacts/` – specs, dev plan, checklists, and process docs
- Core artifacts added and reviewed:
  - `artifacts/spec/FuncTechSpec.md`
  - `artifacts/spec/API_Definition.md` (initial version)
  - `artifacts/DevPlan.md` (this document)
  - `artifacts/DevProgress.md`
  - `artifacts/CodingStandards.md` and `artifacts/DevProcess.md` (if present)
- Basic tooling and conventions established (e.g., package scripts, lint/test commands).

**Status:** Done. No further AI work needed for this sprint unless these docs change.

---

## 2. Sprint 1 – Frontend Shell + Stubbed Localization UX (Completed)

**Goal:** A working web UI in `apps/web/` that feels like a real app, wired to a **fake** localization response, suitable for early demos and UX validation.

### 2.1 Objectives

The Sprint 1 frontend now exists and should generally align with the FuncTechSpec:

- **Login / access gate**
  - Simple stub login form (email + password or equivalent).
  - No real authentication; any values are accepted.
  - On “login”, the app routes to the main poster localization experience.

- **Poster Localizer experience**
  - Dark, cinematic UI with glassmorphism and subtle transitions.
  - Upload control for a poster image (client-side handling).
  - BCP-47-style language selector (e.g., `es-MX`, `fr-FR`, `pt-BR`, `ja-JP`).
  - “Localize Poster” or equivalent CTA button.
  - Processing UX:
    - Animated processing state (spinner or progress bar).
    - Stage messages hinting at the pipeline (OCR / translation / inpainting).
  - Result view:
    - Before/after poster display (may be using placeholder images).
    - Timing breakdown per stage (stubbed or fake data).
    - Simple error state for failures.

- **Stub API integration**
  - Frontend code currently calls a fake or stubbed localization API (e.g. via a hook/module).
  - The shapes of the response are aligned conceptually with the final API, but actual HTTP calls may still be mocked or local.

- **Smoke tests**
  - Rendering of login page and navigation into the main app.
  - Core components of the poster localization page (upload, language, button).
  - UI behavior when the stubbed localization “completes”.

### 2.2 Definition of Done (Sprint 1)

- Frontend builds and runs locally (e.g., via Vite dev server).
- You can:
  - “Log in”
  - Upload a poster
  - Choose a target language
  - Click localize and see:
    - A processing state
    - A “localized result” view backed by stubbed behavior
- UI feels cinematic and demo-worthy.
- No backend dependency; localization behavior is still mocked on the frontend.

**Status:** Done. Sprint 1 should **not** be modified during Sprint 2 except for necessary wiring to the real backend API once it exists.

---

## 3. Sprint 2 – Backend API + Async Mock Pipeline (Current)

**Goal:** Introduce a real backend service in `apps/api/` using FastAPI that implements the **authoritative async job API** described in `API_Definition.md`, with a **mock localization pipeline**, and wire the existing frontend to it.

This sprint is all about giving the app a **real spine**: actual HTTP endpoints, background jobs, progress, and timing data — even though the “localization” is still fake.

### 3.1 Backend Objectives

Implement the following in `apps/api/`:

- **FastAPI app skeleton**
  - A FastAPI application with a clean package layout (e.g., `app/main.py`, `app/models.py`, `app/services/…`).
  - Startup time recorded for uptime reporting.
  - Configurable via environment variables (see FuncTechSpec).

- **Endpoints (as per API_Definition v0.2)**
  - `GET /health`
    - Returns basic liveness JSON with status, uptimeSeconds, and version.
  - `POST /v1/localization-jobs`
    - Accepts `multipart/form-data`:
      - `file` (JPEG/PNG poster)
      - `targetLanguage` (BCP-47)
      - Optional `sourceLanguage`, `jobMetadata`
    - Validates inputs, enforces size and MIME limits.
    - Creates a new **localization job** and returns `202 Accepted` with job metadata.
  - `GET /v1/localization-jobs/{jobId}`
    - Returns job status, progress, and, when complete, the mock result payload.

- **Async job model**
  - In-memory job store keyed by `jobId`.
  - Job statuses: `queued`, `processing`, `succeeded`, `failed` (plus `canceled` reserved for future).
  - Background task or worker that:
    - Transitions a job through `queued → processing → succeeded/failed`.
    - Simulates pipeline stages (OCR, translation, inpaint, packaging).
    - Updates `progress.stage`, `progress.percent`, and `stageTimingsMs`.

- **Mock localization pipeline**
  - No external providers yet; no real OCR/translation/inpainting.
  - A `LocalizationEngine` or pipeline interface (e.g., `LocalizationPipeline` or `LocalizationEngine`) with at least a mock implementation.
  - Simulates realistic timing:
    - Millisecond timings per stage.
    - Total processing time calculation.
  - Returns:
    - A “localized” image URL that can be:
      - The original image
      - A static placeholder
      - A trivial server-side derivation
    - Optional `thumbnailUrl` if convenient.
    - A small `detectedText` array with normalized bounding boxes in `[0.0, 1.0]` coordinate space, even if stubbed.

- **Error handling and logging**
  - Standard error envelope with:
    - `error.code` (e.g., `INVALID_INPUT`, `NOT_FOUND`, `UNSUPPORTED_MEDIA_TYPE`, `INTERNAL_ERROR`).
    - `error.message` (end-user safe, no stack traces).
  - 400/404/413/415/500 mapped appropriately.
  - Basic logging for:
    - Job creation
    - Job progression/completion
    - Errors and exceptions
  - Support a DEBUG toggle via environment variable for more verbose logs.

- **Tests (pytest)**
  - Happy-path health check.
  - Happy-path job creation and polling.
  - Error cases: unknown jobId, missing fields, bad media type, oversized file.
  - All runnable from repo root via `pytest` or equivalent command.

Detailed tasks, file paths, and interface expectations for Sprint 2 are captured in:

- `artifacts/DevChecklist_Sprint2.md`

AI assistants should treat that checklist as **the primary execution guide** for Sprint 2, checking off items as they are completed.

### 3.2 Frontend Integration Objectives

Once the backend is up and stable:

- Update the existing frontend API client (in `apps/web/`) to call:
  - `POST /v1/localization-jobs` for job creation.
  - `GET /v1/localization-jobs/{jobId}` for polling.
- Use environment-based configuration for the backend base URL (e.g., `VITE_API_BASE_URL`).
- Wire the existing “processing” UI to:
  - Interpret `status` (`queued`, `processing`, `succeeded`, `failed`).
  - Display progress percentage and stage labels when present.
  - Show timing breakdown from `result.processingTimeMs`.
- Show friendly error messaging when the backend returns an error envelope or is unreachable.

The frontend **look and feel** should not be heavily modified in Sprint 2; the focus is on wiring it to the real API.

### 3.3 Definition of Done (Sprint 2)

- Backend:
  - FastAPI app runs locally (e.g., via Uvicorn).
  - All Sprint 2 checklist items that are in scope are ticked.
  - Tests pass.
  - API behavior matches `API_Definition.md` v0.2 exactly (field names, status codes, shapes).
- Frontend:
  - Uses the real backend API for job creation and polling.
  - Shows progress and timing data from real backend responses.
  - Handles errors gracefully.
- End-to-end demo:
  - You can:
    - Start backend.
    - Start frontend.
    - Log in, upload a poster, choose a language, and see:
      - A real async job flow.
      - Mock but plausible progress and timing.
      - A “localized” image URL returned by the backend.

---

## 4. Sprint 3 – First Real Pipeline Path (Planned)

**Goal:** Replace the mock localization engine with a **real AI-driven pipeline** on a constrained subset of posters, while preserving the same API contract and frontend behavior.

This sprint is not required to get to an impressive demo, but it turns the system from a “fake but convincing spine” into a **genuinely intelligent** tool.

### 4.1 Objectives (Conceptual)

- **Provider integrations**
  - Implement provider-agnostic clients behind interfaces such as:
    - OCR client (e.g., Google Vision, Tesseract, or equivalent).
    - Translation client (e.g., Claude, other LLM).
    - Inpainting client (e.g., Replicate/SDXL, or other image model).
  - All vendor-specific details must be hidden behind the pipeline interface and mapped into the unified `result` shape.

- **Real pipeline orchestration**
  - Orchestrate:
    - OCR → localized copy suggestion → inpainting → text placement.
  - Respect business rules from `FuncTechSpec.md` where feasible:
    - Titles vs taglines vs credits.
    - “Don’t translate” vs “localize creatively” fields.
    - Basic role classification and credits handling.

- **Performance and timing**
  - Measure and return real timings for each stage.
  - Ensure the UI can handle slightly longer processing times gracefully.

- **Robust error handling**
  - Map vendor failures to:
    - `*_MODEL_ERROR`
    - `*_MODEL_TIMEOUT`
  - Keep error envelopes vendor-neutral.

- **Tests and traceability**
  - Mock provider responses for unit tests.
  - Ensure the pipeline can be exercised and validated without calling real services in CI.

### 4.2 Scope Constraints

- Limit to relatively “simple” posters:
  - Mostly horizontal English text.
  - No curved titles or extreme typographic layouts.
- No requirement yet to handle:
  - PSD input
  - Per-object template config
  - Full marketing/localization workflow with roles and approvals

Further sprints can expand into these areas once the basic live pipeline is proven.

---

## 5. Future Direction – Template Workflow & PSD-Aware Localization (Deferred)

The FuncTechSpec (and our design discussions) outline a richer **template-based workflow** involving:

- A “Marketing Localization Lead” defining per-poster templates.
- AI-assisted auto-tagging of text regions from flat images (and later PSD layers).
- Human-editable JSON templates describing:
  - Which regions are locked vs localizable.
  - Expected roles, fonts, and alignment.
  - FPO vs final content zones.
- Multi-locale generation off a single template.

These are powerful value-add features but are **explicitly out of scope** for the current PoC sprints. They may become:

- Sprint 4+: Template editor UI and template persistence.
- Sprint X: PSD input and PSD export with localized text layers.

For now, the DevPlan treats these as **future opportunities**, not current objectives.

---

## 6. Using DevProgress.md

Alongside this DevPlan, we maintain a **progress log** in `artifacts/DevProgress.md`.

Guidelines:

- After each significant AI or manual coding session:
  - Append a new entry with:
    - Date/time
    - Sprint (0/1/2/3)
    - Mode (e.g., “Cursor IMPLEMENTATION_MODE”, “Manual refactor”)
    - Summary of work
    - Key files touched
    - Tests run and outcomes
- AI assistants are allowed to append to `DevProgress.md` **only when explicitly instructed**, and must never rewrite or delete existing history.

The combination of:

- `DevPlan.md` (roadmap)
- `DevChecklist_Sprint2.md` (detailed Sprint 2 tasks)
- `DevProgress.md` (journal)

gives both humans and AIs a clear understanding of where we are and what comes next.

---

## 7. How AI Assistants Should Use This Plan

When an AI assistant (Cursor, Claude, ChatGPT) is asked to work on this repo, it should:

1. Read:
   - `artifacts/spec/FuncTechSpec.md`
   - `artifacts/spec/API_Definition.md`
   - This `artifacts/DevPlan.md`
   - Any relevant sprint checklist (e.g., `artifacts/DevChecklist_Sprint2.md`)
2. Confirm which sprint and which subset of tasks it has been assigned.
3. Propose or internally plan a small batch of file edits.
4. Implement those edits, keeping changes localized and coherent.
5. Run tests where applicable.
6. Summarize:
   - What was changed
   - Which checklist items were completed
   - Any follow-ups or questions
7. (When instructed) Append an entry to `artifacts/DevProgress.md`.

If the human asks for changes that contradict this plan or the spec files, the assistant should:

- Call out the conflict explicitly.
- Ask whether to:
  - Update the plan/specs, or
  - Adjust the requested work to stay in alignment.

---

## 8. Adjustments

This plan is intentionally lightweight and may evolve as we learn:

- If Sprint 2 proves larger than expected, we can:
  - Defer some parts to 2.1 / 2.2 sub-sprints.
- If Sprint 3 is too ambitious, we can:
  - Narrow the scope (e.g., OCR + translation only, deferred inpainting).
- If new business insights emerge from studio conversations, we can:
  - Add new sprints or adjust goals to highlight the most impressive capabilities.

For now, Sprints 1 and 2 are the **core path** to a compelling, demo-ready PoC:

- A polished cinematic frontend.
- A real backend with an async job model and mock pipeline.
- A clean, extensible architecture ready to accept real AI providers in Sprint 3 and beyond.
