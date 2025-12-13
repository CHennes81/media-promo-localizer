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

### 2025-12-11 – [Sprint 3] batch 2: line-level OCR regions, debug payload, and UI improvements

- Mode: IMPLEMENTATION_MODE
- Initiator: Cursor / Claude
- Summary:
  - Created `DebugTextRegion` model with id, role, bbox_norm (x, y, width, height), original_text, translated_text, is_localizable.
  - Updated OCR client to group words into single-line regions using vertical clustering based on y-coordinate overlap.
  - Enhanced role detection with credits heuristics (bottom position > 0.75, wide/short bbox, high character density).
  - Added `DebugInfo` model and extended `JobResult` with optional `debug` field containing regions and timings.
  - Configured logging with both StreamHandler (stdout) and FileHandler (`logs/app.log`) with shared format.
  - Updated `LiveLocalizationEngine` to create debug regions after OCR, populate translated_text after translation, and emit structured log messages (`[OCR]` and `[Xlate]`).
  - Updated frontend `ResultView` to show single large localized image (removed side-by-side comparison).
  - Added "View Details" button and "Show OCR Boxes" toggle.
  - Implemented Details dialog component with table showing all debug regions (Role, BBox, Original text, Translated text, Localizable).
  - Implemented purple OCR bounding-box overlays on localized image when toggle is enabled.
  - Updated TypeScript types to include `debug` field in `LocalizationResult`.
- Files touched (high level):
  - `apps/API/app/models.py` (added DebugTextRegion, DebugInfo, updated JobResult, ProcessingTimeMs)
  - `apps/API/app/clients/ocr_client.py` (added line-level grouping with vertical clustering)
  - `apps/API/app/services/live_engine.py` (added debug region creation, log messages, debug payload)
  - `apps/API/app/main.py` (configured logging with file handler)
  - `apps/web/src/components/ResultView.tsx` (single image layout, Details dialog, OCR overlays)
  - `apps/web/src/components/ResultView.css` (updated styles for new layout)
  - `apps/web/src/types/api.ts` (added DebugTextRegion, DebugInfo types)
  - `apps/API/tests/test_live_engine.py` (updated to verify debug payload)
- Tests:
  - pytest (tests updated to verify debug payload)
- Outcome: completed
- Notes:
  - OCR client now groups words into line-level regions, especially useful for credits bands.
  - Debug payload is optional and additive to existing API contract (backward compatible).
  - Logging writes to both stdout and `logs/app.log` with structured messages for each region.
  - Frontend Details dialog shows all debug regions in a scrollable table.
  - OCR box overlays use normalized bounding boxes multiplied by rendered image dimensions.
  - Credits detection heuristics help identify dense text bands at the bottom of posters.

### 2025-12-11 – [Sprint 3] batch 2 follow-up: wire debug UI and add per-job logging

- Mode: IMPLEMENTATION_MODE
- Initiator: Cursor / Claude
- Summary:
  - Fixed frontend ResultView to properly handle debug state and enable buttons when debug data exists.
  - Fixed OCR overlay positioning by ensuring container is relatively positioned and overlays have correct z-index.
  - Added comprehensive external call logging to OCR client (before/after with timestamps, status codes, durations).
  - Added comprehensive external call logging to Translation client (before/after with timestamps, status codes, durations).
  - Changed region logs from DEBUG to INFO level so they appear in logs/app.log.
  - Added job-level summary logging after completion with region counts by role and total processing time.
  - Enhanced error logging in OCR client to include job context.
  - All logging now writes to both stdout and logs/app.log as configured.
- Files touched (high level):
  - `apps/web/src/components/ResultView.tsx` (fixed imageRef duplicate, verified debug state handling)
  - `apps/web/src/components/ResultView.css` (fixed overlay positioning with z-index)
  - `apps/API/app/clients/ocr_client.py` (added before/after call logging with job_id, enhanced error logging)
  - `apps/API/app/clients/translation_client.py` (added before/after call logging with job_id)
  - `apps/API/app/services/live_engine.py` (changed region logs to INFO, added job summary, pass job_id to clients)
- Tests:
  - No new tests added (existing tests should still pass with optional job_id parameter)
- Outcome: completed
- Notes:
  - View Details button and Show OCR Boxes toggle now properly enable when debug data is present.
  - OCR overlays render correctly with purple bounding boxes when toggle is enabled.
  - All per-job logs (external calls, regions, translations, summaries) now appear in both stdout and logs/app.log.
  - Log messages include job_id for traceability throughout the pipeline.
  - Region logs truncate text to 120 characters for readability.

### 2025-12-11 – [Sprint 3] logging first pass: comprehensive structured logging

- Mode: IMPLEMENTATION_MODE
- Initiator: Cursor / Claude
- Summary:
  - Added request logging middleware that logs all HTTP requests with method, path, status, duration, request ID, and client IP.
  - Enhanced logging configuration to support TRACE_CALLS environment variable for optional method entry/exit tracing.
  - Created logging utilities module with trace_calls decorator and service call wrapper.
  - Added comprehensive service call logging to OCR, Translation, and Inpainting clients (before/after with timestamps, status codes, durations, payload/response sizes).
  - Added pipeline stage logging to live_engine and mock_engine (start/end of each stage with durations and counts).
  - Enhanced config logging on startup with resolved values (redacting secrets).
  - Applied trace decorator to key functions in live_engine (only active when TRACE_CALLS=true).
  - Created frontend logger utility with structured logging format.
  - Added frontend logging around localization action (button click, job creation, success/failure, with mode detection).
  - Added tests for request middleware (X-Request-Id header, request logging).
- Files touched (high level):
  - `apps/API/app/config.py` (added TRACE_CALLS env var)
  - `apps/API/app/main.py` (added RequestLoggingMiddleware, enhanced config logging)
  - `apps/API/app/utils/logging.py` (new - trace decorator and service call wrapper)
  - `apps/API/app/clients/ocr_client.py` (enhanced logging with request_id, payload size, response size)
  - `apps/API/app/clients/translation_client.py` (enhanced logging with request_id, payload size, response size)
  - `apps/API/app/clients/inpainting_client.py` (added stub service call logging)
  - `apps/API/app/services/live_engine.py` (added pipeline stage logging, applied trace decorator)
  - `apps/API/app/services/mock_engine.py` (added pipeline stage logging)
  - `apps/web/src/utils/logger.ts` (new - frontend logger utility)
  - `apps/web/src/components/LocalizationWorkspace.tsx` (added logging around localization action)
  - `apps/web/src/services/mockLocalizationService.ts` (added logging to createJob)
  - `apps/API/tests/test_middleware.py` (new - tests for request middleware)
- Tests:
  - pytest (added middleware tests)
- Outcome: completed
- Notes:
  - All logs write to both stdout and `apps/API/logs/app.log`.
  - Request middleware generates X-Request-Id header for correlation.
  - Service call logs include correlation IDs (request_id and job_id when available).
  - Pipeline stage logs include stage name, duration, and relevant counts (regions, words, etc.).
  - TRACE_CALLS decorator is a no-op unless TRACE_CALLS=true, allowing verbose debugging without code changes.
  - Frontend logs include component, action, and context for easy filtering.
  - All logging is structured and grep-friendly for debugging without DevTools.

### 2025-12-XX – [Sprint 3] pipeline skip step env vars and skip-event logging

- Mode: IMPLEMENTATION_MODE
- Initiator: Cursor / Claude
- Summary:
  - Added four boolean environment variables (SKIP_OCR, SKIP_TRANSLATION, SKIP_INPAINT, SKIP_PACKAGING) that allow skipping individual pipeline stages for debugging/testing.
  - Both LiveLocalizationEngine and MockLocalizationEngine respect these skip flags.
  - Added mandatory structured logging when a step is skipped: PipelineStageSkipped log with job, stage, reason, env var name, and value.
  - Enhanced PipelineStageStart and PipelineStageEnd logs to include skipped=true flag when a stage is skipped.
  - When a stage is skipped, the engine still advances job progress, persists state, and provides valid data for downstream steps.
  - Skip behavior per stage:
    - SKIP_OCR: Uses empty list of text regions (and empty debug regions).
    - SKIP_TRANSLATION: Sets translated_text = original_text for all regions (identity translation).
    - SKIP_INPAINT: Passes through original image bytes as the "localized" image.
    - SKIP_PACKAGING: Still returns valid job result object using existing in-memory/localized image output.
  - Added comprehensive tests for skip behavior (SKIP_TRANSLATION and SKIP_OCR) for both live and mock engines.
- Files touched (high level):
  - `apps/API/app/config.py` (added SKIP_OCR, SKIP_TRANSLATION, SKIP_INPAINT, SKIP_PACKAGING env vars)
  - `apps/API/app/main.py` (added skip env var logging in config block)
  - `apps/API/app/services/live_engine.py` (added skip flag checks, PipelineStageStart/Skipped/End logging, skip behavior implementation)
  - `apps/API/app/services/mock_engine.py` (added skip flag checks, PipelineStageStart/Skipped/End logging, skip behavior implementation)
  - `apps/API/tests/test_live_engine.py` (added tests for SKIP_TRANSLATION and SKIP_OCR)
  - `apps/API/tests/test_mock_engine.py` (new - tests for mock engine skip behavior)
- Tests:
  - pytest (added skip behavior tests)
- Outcome: completed
- Notes:
  - All skip env vars default to false (normal operation).
  - Skip env vars are logged at startup in the config logging block.
  - When a stage is skipped, PipelineStageStart, PipelineStageSkipped, and PipelineStageEnd logs are all emitted with skipped=true on the end log.
  - Jobs complete successfully even when stages are skipped, ensuring deterministic behavior for testing.
  - Skip mode is useful for testing individual pipeline stages in isolation or debugging specific stage issues.
