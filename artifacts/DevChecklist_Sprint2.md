# Sprint 2 – Backend Development Checklist (FastAPI, Mock Pipeline)

Repo: `CHennes81/media-promo-localizer`
Scope: **Backend only**, `apps/api/` only. **Do not modify `apps/web/`.**

Specs are authoritative:

- `artifacts/spec/FuncTechSpec.md`
- `artifacts/spec/API_Definition.md` (v0.2, `/v1/localization-jobs`, `/health`)

---

## 0. Grounding & Setup

- [ ] 0.1 Read `FuncTechSpec.md` (sections 2, 3, 8–13) and confirm understanding.
- [ ] 0.2 Read `API_Definition.md` v0.2 and confirm endpoints & JSON shapes.
- [ ] 0.3 Verify project layout and create `apps/api/` package if it does not exist.

---

## 1. FastAPI App Skeleton

- [ ] 1.1 Create `apps/api/app/main.py` with:
  - FastAPI app instance.
  - Startup timestamp to compute uptime.
- [ ] 1.2 Add routing stubs for:
  - `GET /health`
  - `POST /v1/localization-jobs`
  - `GET /v1/localization-jobs/{jobId}`
- [ ] 1.3 Implement `GET /health` to return JSON like:
  - status: `"ok"`
  - uptimeSeconds: numeric uptime in seconds
  - version: `"0.2.0"`

---

## 2. Config & Constants

- [ ] 2.1 Create `apps/api/app/config.py` to read env/config values:
  - `LOCALIZATION_MODE` (default `"mock"`)
  - `MAX_UPLOAD_MB` (e.g. 20)
  - Allowed mime types (`image/jpeg`, `image/png`).
- [ ] 2.2 Expose a simple config object used by routes & services.

---

## 3. API Schemas & Internal Models

- [ ] 3.1 Define Pydantic models (v2 style) in `apps/api/app/models.py` that match `API_Definition.md`:
  - `JobStatus` enum: `queued`, `processing`, `succeeded`, `failed`.
  - `Progress` with `stage`, `percent`, `stageTimingsMs`.
  - `JobResult` with:
    - `imageUrl`
    - `thumbnailUrl` (optional)
    - `processingTimeMs`
    - `language`, `sourceLanguage`
    - optional `detectedText[]` (with `text`, normalized `boundingBox`, `role`).
  - `ErrorInfo` for the `error` object on jobs.
  - `CreateJobResponse` (202 payload).
  - `GetJobResponse` (job status/result shape).
- [ ] 3.2 Define internal `LocalizationJob` model:
  - `jobId`, `status`, `createdAt`, `updatedAt`
  - `targetLanguage`, `sourceLanguage`
  - `progress`, `result`, `error`
  - any internal fields needed (e.g., file metadata).
- [ ] 3.3 Ensure all timestamps are ISO-8601 UTC when serialized.

---

## 4. In-Memory Job Store

- [ ] 4.1 Create `apps/api/app/services/job_store.py` with an interface like:
  - `create_job(...) -> LocalizationJob`
  - `get_job(job_id: str) -> LocalizationJob | None`
  - `update_job(job: LocalizationJob) -> None`
- [ ] 4.2 Implement an in-memory dictionary-based store (single-process only).
- [ ] 4.3 Enforce a soft limit on number of jobs (e.g. 50) and evict or reject when exceeded.

---

## 5. Mock Localization Engine & Pipeline

- [ ] 5.1 Create `apps/api/app/services/mock_engine.py` with a clear interface, e.g.:
  - `async def run(job: LocalizationJob) -> LocalizationJob`
- [ ] 5.2 Simulate stages:
  - `ocr` → `translation` → `inpaint` → `packaging`
  - Update `job.progress.stage`, `job.progress.percent`, and `stageTimingsMs`.
- [ ] 5.3 Populate a plausible `result`:
  - Fake `imageUrl`/`thumbnailUrl` (e.g. `/static/mock/<jobId>.png` or similar placeholder).
  - `processingTimeMs` with `ocr`, `translation`, `inpaint`, `total`.
  - `language` and `sourceLanguage`.
  - `detectedText[]` with:
    - 2–4 regions (`title`, `tagline`, `credits`, etc.).
    - **Normalized** bounding boxes (`[x1, y1, x2, y2]` in 0–1).
- [ ] 5.4 Mark at least one region as “tricky/FPO” via role or text content so we can demo that concept later.

---

## 6. Implement Endpoints

### 6.1 POST /v1/localization-jobs

- [ ] 6.1.1 Parse `multipart/form-data`:
  - `file` (required, JPEG/PNG, enforce size limit).
  - `targetLanguage` (required).
  - `sourceLanguage`, `jobMetadata` (optional).
- [ ] 6.1.2 Validate inputs and return 400 / 415 / 413 with error envelope when invalid.
- [ ] 6.1.3 Create new job via job store with:
  - `status = "queued"`
  - timestamps set
- [ ] 6.1.4 Schedule background processing (FastAPI `BackgroundTasks` or equivalent) to:
  - set status to `processing`
  - call `mock_engine.run(job)`
  - on success: mark job `succeeded`, fill `result`
  - on failure: mark job `failed`, fill `error`
- [ ] 6.1.5 Return 202 Accepted with `CreateJobResponse` matching spec.

### 6.2 GET /v1/localization-jobs/{jobId}

- [ ] 6.2.1 Look up job in store; if missing, return 404 with error envelope (`NOT_FOUND`).
- [ ] 6.2.2 Map internal job to `GetJobResponse`:
  - include `jobId`, `status`, `createdAt`, `updatedAt`
  - include `progress` (if present)
  - include `result` or `error` depending on status
- [ ] 6.2.3 Ensure response shape and enums exactly match `API_Definition.md`.

---

## 7. Error Handling & Logging

- [ ] 7.1 Implement a helper to build standard error envelopes, e.g.:
  - error.code: values like `INVALID_INPUT`, `NOT_FOUND`, `UNSUPPORTED_MEDIA_TYPE`, etc.
  - error.message: human-readable but non-leaky description.

- [ ] 7.2 Map Python/FastAPI errors to:
  - 400 → `INVALID_INPUT`
  - 404 → `NOT_FOUND`
  - 413 → `PAYLOAD_TOO_LARGE`
  - 415 → `UNSUPPORTED_MEDIA_TYPE`
  - 500 → `INTERNAL_ERROR`
- [ ] 7.3 Configure logging (Python `logging`):
  - Global logger created in `main.py`
  - INFO by default, DEBUG toggle via env var.
  - Log job lifecycle events (created / started / succeeded / failed) and errors.

---

## 8. Tests (pytest)

- [x] 8.1 Add `tests/` package for backend.
- [x] 8.2 Test `GET /health`:
  - status 200
  - body contains `status: "ok"` and `uptimeSeconds`.
- [x] 8.3 Test `POST /v1/localization-jobs`:
  - valid image + targetLanguage → 202 + jobId.
  - missing `targetLanguage` → 400 with `error.code = "INVALID_INPUT"`.
  - bad mime type → 415 with `error.code = "UNSUPPORTED_MEDIA_TYPE"`.
- [x] 8.4 Test `GET /v1/localization-jobs/{jobId}`:
  - unknown jobId → 404 with `error.code = "NOT_FOUND"`.
  - existing job after mock completion → 200 with `status = "succeeded"` and non-null `result`.
- [x] 8.5 Ensure tests run via `pytest` from repo root and document the command in a comment or README. [NOTE: Manual fix applied to main.py to avoid circular import on "_startup_time". Tests run manually via "pythos -m pytest" with local venv at project root.]

---

## 9. Cleanup & Review

- [ ] 9.1 Run formatter/linter (e.g. `black`, `ruff`) if configured.
- [ ] 9.2 Sanity-check types, docstrings, and module organization.
- [ ] 9.3 Confirm API responses still match `API_Definition.md` exactly.
- [ ] 9.4 Add a brief note (e.g., in `README` or a comment in `FuncTechSpec.md`) that Sprint 2 backend is implemented with a **mock** pipeline only.
