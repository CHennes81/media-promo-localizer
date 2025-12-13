# ChatGPT_Control.md

## Paramount Image Xlate PoC – Current State Handoff

**Purpose:**  
This document captures the authoritative project state, architecture decisions, known bugs, and next actions so a new ChatGPT thread can resume work without loss of context.

---

## 1. High‑Level Status (as of 2025‑12‑12)

**Overall:**

- Frontend and backend are now correctly wired.
- Frontend always calls the live backend API (no mock mode).
- OCR (Google Vision) is working end‑to‑end.
- Translation (OpenAI) _executes successfully_ but the job fails due to backend logging/exception‑handling bugs.
- UI shows “Processing…” because the job crashes during translation and transitions to `failed`.

This is **real progress**: failures are now deterministic, logged, and diagnosable.

---

## 2. Architecture (Authoritative)

### Frontend

- **Never selects backend mode**
- Always calls backend HTTP API:
  - `POST /v1/localization-jobs`
  - `GET /v1/localization-jobs/{jobId}`
- API base URL:
  - `import.meta.env.VITE_API_BASE_URL`
  - defaults to `http://localhost:8000`
- No runtime mock logic remains.

### Backend

- Controls execution mode via env var only:
  - `LOCALIZATION_MODE=live`
- Live stack:
  - OCR: Google Vision (`images:annotate`)
  - Translation: OpenAI Chat Completions (`gpt-4o-mini`)
  - Inpainting: Stub (expected for now)

### Separation of Concerns

- Frontend: UI + API calls only
- Backend: orchestration, OCR, translation, logging, job lifecycle
- Mock services exist **only** for tests / storybook

---

## 3. What Is Working

### ✅ Backend startup

- `trace_calls` import fixed in `live_engine.py`
- Backend starts cleanly under Uvicorn

### ✅ Job creation

- `POST /v1/localization-jobs` returns `202 Accepted`
- Job ID created and persisted

### ✅ OCR pipeline

- Google Vision call succeeds (`HTTP 200`)
- Example run:
  - 186 words detected
  - 185 line regions produced
- OCR regions logged with:
  - normalized bounding boxes
  - text
  - role classification (credits / other)

### ✅ Logging

- Structured logs now emitted for:
  - RequestStart / RequestEnd
  - PipelineStageStart / End
  - ServiceCall / ServiceResponse
  - JobCreated / JobStarted / JobUpdated

---

## 4. Current Failure (Root Cause Identified)

### Symptom

- Job enters TRANSLATION stage
- OpenAI request returns `HTTP 200 OK`
- Job transitions to `failed`
- UI appears “stuck” until job state is polled

### Actual Error (Backend Bug)

```
NameError: name 'correlation_str' is not defined
UnboundLocalError: cannot access local variable 'content' where it is not associated with a value
```

### Where

`apps/API/app/clients/translation_client.py`

### Why

- `correlation_str` referenced in exception/logging path but never defined
- `content` referenced in except block without guaranteed assignment
- Error occurs _after_ successful OpenAI response while logging / handling output

---

## 5. Secondary Issue (Progress Tracking)

- Logs show:
  - `JobUpdated stage=TRANSLATION`
- Job GET response still shows:
  - `progress.stage = "ocr"`
  - `percent = 25`

**Cause:**  
Progress update is logged but not persisted _before_ translation call.
When translation crashes, progress never advances.

---

## 6. Immediate Required Fixes (Next CodeGen Task)

### A. Translation client hardening

- Always define `correlation_str` before try/except
- Initialize `content = None` before try
- Never reference unset variables in except/finally
- Log ServiceResponse success path explicitly
- Ensure logging cannot throw

### B. Job progress correctness

- Persist `stage="translation"`, `percent=50` **before** calling OpenAI
- On translation failure:
  - progress.stage remains `translation`
  - job status becomes `failed`

---

## 7. Known Design Issue (Not a Bug, But Important)

### OCR granularity

- OCR currently yields near word‑level regions
- This is **not acceptable** for translation quality or cost

**Planned fix (after translation client is stable):**

- Group OCR results into true visual lines via Y‑axis clustering
- Translate lines, not words

---

## 8. What NOT To Change

- Do **not** reintroduce frontend mock mode
- Do **not** add frontend knowledge of backend implementation
- Do **not** reduce logging yet (it is currently essential)

---

## 9. Recommended Next Prompt (for new ChatGPT thread)

> “Load ChatGPT_Control.md and fix the translation_client crash and job progress persistence per section 6. Do not change frontend.”

---

**This document is the single source of truth for resuming work.**
