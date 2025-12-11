# Sprint 3 – Live Pipeline & Provider Integration Checklist

> **Version History**
>
> - 2025‑12‑11 – v1.0 – Initial checklist capturing Sprint 3 (Batch 1) work for live OCR + translation pipeline.

---

Repo: `CHennes81/media-promo-localizer`
Scope: **Backend only**, `apps/API/` only. **Do not modify `apps/web/`.**

Authoritative specs / control docs:

- `artifacts/FuncTechSpec.md`
- `artifacts/API_Definition.md`
- `artifacts/API_Providers.md`
- `artifacts/DevPlan.md`
- `artifacts/DevProcess.md`
- `artifacts/DevChecklist_Sprint3.md` (this file)
- `artifacts/DevProgress.md`

Cursor should treat these documents as the **source of truth** for behavior and API contracts.

---

## 0. Grounding & Setup

- [x] 0.1 Read `FuncTechSpec.md` sections covering providers and live pipeline behavior.
- [x] 0.2 Read `API_Definition.md` and confirm request/response shapes for `/v1/localization-jobs` and `/health`.
- [x] 0.3 Read `API_Providers.md` and confirm selected providers for:
  - OCR (Google Cloud Vision for now).
  - Translation (OpenAI chat completions).
  - Inpainting (stubbed for this sprint; real provider deferred).
- [x] 0.4 Read `DevProcess.md` (branching, CI, testing) and `DevPlan.md` (Sprint 3 scope).
- [x] 0.5 Confirm local backend environment works:
  - `cd apps/API`
  - `pip install -r requirements.txt`
  - `python -m pytest tests/ -v` (existing tests should pass before new work begins).

---

## 1. Client Interfaces & Config

- [x] 1.1 Create `app/clients/interfaces.py` with protocol-style interfaces:
  - `IOcrClient`, `ITranslationClient`, `IInpaintingClient`.
  - Typed result structures: `OcrResult`, `TranslatedRegion`.
- [x] 1.2 Extend `app/config.py` settings to support:
  - `LOCALIZATION_MODE` (`"mock"` / `"live"`).
  - Provider configuration: `OCR_API_KEY`, `OCR_API_ENDPOINT`, `OPENAI_API_KEY`, `TRANSLATION_MODEL`.
- [x] 1.3 Ensure `Settings` exposes these via environment variables and that defaults keep CI in **mock mode**.

---

## 2. OCR Client – Google Cloud Vision

- [x] 2.1 Implement `CloudOcrClient` in `app/clients/ocr_client.py`:
  - Uses `httpx.AsyncClient` and Google Vision REST API endpoint.
  - Accepts raw image bytes and returns a list of `OcrResult`.
- [x] 2.2 Normalize bounding boxes from provider format to `[0, 1]` relative coordinates.
- [x] 2.3 Map provider errors / timeouts to clean exceptions usable by the service layer.
- [x] 2.4 Add tests in `tests/test_ocr_client.py`:
  - Success with mocked `httpx.AsyncClient`.
  - API error case.
  - Timeout case.
  - Missing API key case.

---

## 3. Translation Client – OpenAI

- [x] 3.1 Implement `LlmTranslationClient` in `app/clients/translation_client.py`:
  - Uses `AsyncOpenAI` client from `openai>=2.x`.
  - Calls chat completions API with JSON response format.
- [x] 3.2 Implement prompting per `FuncTechSpec`:
  - Transcreation for taglines.
  - Preserve proper names in credits and key art.
  - Do **not** translate URLs, social handles, or locked regions.
- [x] 3.3 Parse JSON response into `TranslatedRegion` objects.
- [x] 3.4 Add tests in `tests/test_translation_client.py`:
  - Success path with mocked `AsyncOpenAI`.
  - API error case.
  - Invalid JSON case.
  - Missing API key case.

---

## 4. Live Localization Engine

- [x] 4.1 Implement `LiveLocalizationEngine` in `app/services/live_engine.py`:
  - Orchestrates OCR → translation → inpainting → packaging.
  - Uses client interfaces (`IOcrClient`, `ITranslationClient`, `IInpaintingClient`).
- [x] 4.2 Implement heuristic text classification (`classify_text_regions`) to label regions:
  - Titles, taglines, credits, other.
- [x] 4.3 Implement `is_localizable` policy per spec:
  - Lock URLs, social handles, and specific non-translatable regions.
- [x] 4.4 Track per-stage timings:
  - `ocr`, `translation`, `inpaint`, `packaging`, plus `total` in `ProcessingTimeMs`.
  - Use `time.perf_counter()` and ensure each stage reports at least 1ms.
- [x] 4.5 Add tests in `tests/test_live_engine.py`:
  - `test_live_engine_success` – end-to-end happy path with mocks.
  - OCR failure propagates correctly.
  - Translation failure propagates correctly.
  - Classification and localizability helpers behave as expected.

---

## 5. Jobs Router & Mode Switching

- [x] 5.1 Update `app/routers/jobs.py` to select between:
  - Existing mock engine (for `LOCALIZATION_MODE="mock"`).
  - `LiveLocalizationEngine` (for `LOCALIZATION_MODE="live"`).
- [x] 5.2 On `LOCALIZATION_MODE="live"`, validate required environment variables:
  - `OCR_API_KEY`, `OPENAI_API_KEY` (and optionally `OCR_API_ENDPOINT`, `TRANSLATION_MODEL`).
  - Return a clear error if configuration is incomplete.
- [x] 5.3 Ensure job creation and retrieval behavior remains backward compatible with the existing API contract.

---

## 6. Sanity Checks & Regression Tests

- [x] 6.1 Ensure `apps/API/requirements.txt` includes:
  - `pillow>=10.0.0`
  - `openai>=2.0.0`
  - Any other newly required packages (e.g. `httpx`, already present).
- [x] 6.2 Run the full backend test suite:

  ```bash
  cd apps/API
  pip install -r requirements.txt
  python -m pytest tests/ -v
  ```

- [x] 6.3 Confirm:
  - All tests pass (`24 passed`).
  - No new deprecation warnings beyond the known Pydantic v2 config warning.

---

## 7. Manual Smoke Tests (Developer / Chris)

These checks are **manual** and are for Chris, not Cursor:

- [ ] 7.1 Run backend in mock mode:

  ```bash
  cd apps/API
  uvicorn app.main:app --reload
  ```

  - Leave `LOCALIZATION_MODE` unset (defaults to `"mock"`).
  - Submit a sample poster via the frontend and confirm:
    - Job is created and transitions from pending → running → succeeded.
    - Mock result structure matches `API_Definition.md`.

- [x] 7.2 Once API keys are available, test live mode:

  ```bash
  export LOCALIZATION_MODE=live
  export OCR_API_KEY=your_google_cloud_vision_key
  export OPENAI_API_KEY=your_openai_api_key
  # optional:
  # export TRANSLATION_MODEL=gpt-4o-mini
  # export OCR_API_ENDPOINT=https://vision.googleapis.com/v1/images:annotate

  uvicorn app.main:app --reload
  ```

  - Upload a real movie poster.
  - Confirm:
    - OCR finds reasonable text regions.
    - Translation returns localized text in the target language.
    - Processing times are non-zero and logged.

- [x] 7.3 Capture any issues from live tests and log them as new items in:
  - `DevProgress.md` (with timestamps and context).
  - A future `DevChecklist_Sprint3_Batch2` or Sprint 4 checklist for:
    - Real inpainting provider integration.
    - Refining classification heuristics.
    - Performance tuning.

---

> **Completion Criteria for Sprint 3 (Batch 1):**
>
> - All items in sections 0–6 are checked.
> - Manual smoke tests in section 7 have been attempted and any issues recorded.
> - Backend tests are green and `LOCALIZATION_MODE=live` works end-to-end with real providers (assuming valid API keys).
