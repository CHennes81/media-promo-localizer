# Development Progress Log – Media Promo Localizer

> **Version History**
>
> - 2025‑12‑10 – v1.1 – Reinforced that this log is append‑only and that each entry should correspond to a single logical unit of work (AI or human), updated immediately after completion.
> - 2025‑11‑xx – v1.0 – Initial version prior to control‑doc consolidation.

---

**Location:** `artifacts/DevProgress.md`
**Audience:** Human developers and AI coding assistants

This file is a **running journal** of work done on the project.
It is designed so that:

- Humans can quickly see what was done, when, and by whom.
- AI assistants (e.g., Claude) can avoid re-doing work or losing track of context.

Only **append** new entries; do not rewrite or delete history.

---

## 1. Log Format

For each significant change batch (Claude task, human session), append an entry like this:

```markdown
### 2025-12-03 – [Sprint 1] implement login + poster localizer shell

- Mode: IMPLEMENTATION_MODE
- Initiator: Claude / Human
- Summary:
  - Short bullet list of what was done.
- Files touched (high level):
  - apps/web/src/pages/LoginPage.tsx
  - apps/web/src/pages/PosterLocalizerPage.tsx
  - apps/web/src/hooks/useTranslatePoster.ts
- Tests:
  - pnpm lint (pass/fail)
  - pnpm test (pass/fail)
- Outcome: completed / partial / rolled back
- Notes:
  - Any follow-ups, caveats, or questions.
```

Guidelines:

- Keep summaries concise but meaningful.
- If a batch is rolled back, still log it with **Outcome: rolled back** and a short explanation.
- If multiple small commits are part of one conceptual change, aggregate them into a single entry.

---

## 2. Entries

> New entries go **below** this line. Most recent entries at the bottom.

### 2025-12-03 – [Sprint 0] bootstrap repo and artifacts

- Mode: REFINEMENT_MODE
- Initiator: Human
- Summary:
  - Cloned React/Vite template into `media-promo-localizer`.
  - Configured Git remote and verified SSH push/pull.
  - Added `FuncTechSpec.md`, `CodingStandards.md`, and `DevProcess.md` to `artifacts/`.
- Files touched (high level):
  - artifacts/FuncTechSpec.md
  - artifacts/CodingStandards.md
  - artifacts/DevProcess.md
- Tests:
  - pnpm dev (manual sanity check)
- Outcome: completed
- Notes:
  - Repo is ready for Sprint 1 frontend work.

### 2025-12-11 – [Sprint 3] implement live pipeline batch 1 (ocr + translation)

- Mode: IMPLEMENTATION_MODE
- Initiator: Cursor / Claude
- Summary:
  - Added provider-agnostic interfaces for OCR, translation, and inpainting under `app/clients/`.
  - Implemented real OCR client (`CloudOcrClient`) using Google Cloud Vision API REST endpoint.
  - Implemented real translation client (`LlmTranslationClient`) using OpenAI API.
  - Created stub inpainting client (`StubInpaintingClient`) per FuncTechSpec out-of-scope section.
  - Introduced `LiveLocalizationEngine` that orchestrates real OCR + translation with stub inpainting.
  - Added `LOCALIZATION_MODE` configuration switch (mock/live) with provider settings (OCR_API_KEY, OPENAI_API_KEY, etc.).
  - Updated jobs router to select engine based on `LOCALIZATION_MODE` (defaults to mock for backward compatibility).
  - Added comprehensive tests for OCR client, translation client, and live engine with mocked external calls.
- Files touched (high level):
  - `apps/API/app/clients/__init__.py` (new)
  - `apps/API/app/clients/interfaces.py` (new)
  - `apps/API/app/clients/ocr_client.py` (new)
  - `apps/API/app/clients/translation_client.py` (new)
  - `apps/API/app/clients/inpainting_client.py` (new)
  - `apps/API/app/services/live_engine.py` (new)
  - `apps/API/app/config.py` (updated - added provider config)
  - `apps/API/app/routers/jobs.py` (updated - engine selection)
  - `apps/API/requirements.txt` (updated - added pillow, openai)
  - `apps/API/tests/test_ocr_client.py` (new)
  - `apps/API/tests/test_translation_client.py` (new)
  - `apps/API/tests/test_live_engine.py` (new)
- Tests:
  - pytest (tests written, require venv with dependencies installed)
- Outcome: completed
- Notes:
  - Inpainting is still stubbed; future batch can implement actual background removal once spec is updated.
  - To use live mode, set environment variables: `LOCALIZATION_MODE=live`, `OCR_API_KEY`, `OPENAI_API_KEY`.
  - OCR client uses Google Cloud Vision REST API (no SDK required).
  - Translation client uses OpenAI's chat completions API with JSON response format.
  - All external API calls are mocked in tests; no real network calls during test runs.

### 2025-12-11 – [Sprint 3] batch 1 completion and smoke test

- Mode: DOC_UPDATE_MODE
- Initiator: Human / Cursor
- Summary:
  - Sprint 3 Batch 1 (live OCR + translation pipeline) implementation completed and verified.
  - All backend tests passing: `python -m pytest tests/ -v` (24 passed, 1 warning).
  - Fixed timing measurement in `LiveLocalizationEngine` to use `time.perf_counter()` with minimum 1ms per stage.
  - Manual smoke test performed with live pipeline mode.
- Files touched (high level):
  - `artifacts/DevChecklist_Sprint3.md` (updated - marked Batch 1 items complete)
  - `artifacts/DevProgress.md` (updated - added this entry)
- Tests:
  - `python -m pytest tests/ -v` (24 passed, 1 warning)
- Outcome: completed
- Notes:
  - Manual smoke test details:
    - Poster: "Star Trek Into Darkness"
    - Target language: Spanish (Mexico) (es-MX)
    - Job completed successfully with status "succeeded"
    - Processing times recorded: non-zero values for OCR, translation, inpaint, and packaging stages
    - Image visually unchanged due to stub inpainting (expected for Batch 1)
  - System ready for Sprint 3 Batch 2:
    - Implement real inpainting provider behind `IInpaintingClient` interface
    - Improve text role classification heuristics (currently simple keyword-based)
    - Address any QA issues discovered in future testing
  - All Batch 1 checklist items (sections 0-6, section 7.2) marked complete in `DevChecklist_Sprint3.md`
