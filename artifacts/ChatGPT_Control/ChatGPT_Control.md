# ChatGPT_Control.md

**Project:** Media Promo Localizer (Poster Localization PoC)
**Status:** Active Development – OCR & Credits Pipeline Stabilized
**Last Updated:** 2025-12-13

---

## 1. Purpose of This Document

This document exists to:

- Preserve _authoritative project state_ across ChatGPT threads
- Prevent regression, re-derivation, or architectural drift
- Provide a single, canonical handoff artifact for restarting work
- Act as the **source of truth** for Cursor prompts and scope control

This file should always be uploaded or pasted at the start of a new thread.

---

## 2. High-Level System Overview

**Goal:**
Automatically localize movie poster text while preserving layout, typography intent, and spatial fidelity.

**Pipeline Stages (strict order):**

1. Image ingest (full resolution, ≤20MB)
2. OCR (Google Vision, rotation-aware)
3. Translation (LLM, selective, layout-preserving)
4. Inpainting (text removal + re-render)
5. Packaging (final assets)

Each stage can be individually skipped via environment variables for rapid iteration.

---

## 3. Current Architecture (Confirmed Stable)

### Backend

- **Framework:** FastAPI + Uvicorn
- **Language:** Python 3.11
- **OCR:** Google Vision API (DOCUMENT_TEXT_DETECTION)
- **Translation:** OpenAI (gpt-4o-mini currently configured)
- **Inpainting:** Stub (real implementation deferred)
- **Job Model:** Async job lifecycle with polling

### Frontend

- **Framework:** React + Vite
- **Behavior:** Always calls real backend APIs (no runtime mock mode)
- **Polling:** Job status via `/v1/localization-jobs/{jobId}`

---

## 4. Logging & Observability (Critical Achievement)

Logging is now _first-class_ and mandatory.

### Guaranteed Logs

- Application startup & config
- RequestStart / RequestEnd (middleware)
- JobCreated / JobStarted / JobCompleted
- PipelineStageStart / PipelineStageEnd
- PipelineStageSkipped (with env var + value)
- ServiceCall / ServiceResponse (all external APIs)
- OCR summaries (word counts, line counts)
- OCR debug previews (first N reconstructed lines)

### Result

Debugging no longer requires DevTools guessing.
Logs are sufficient to understand system behavior end-to-end.

---

## 5. Environment Variables (Authoritative)

### Global

- `MAX_UPLOAD_MB` (default: 20)
- `LOG_LEVEL`
- `TRACE_CALLS`

### Pipeline Skips (applies to LIVE and MOCK engines)

- `SKIP_OCR`
- `SKIP_TRANSLATION`
- `SKIP_INPAINT`
- `SKIP_PACKAGING`

All skips are explicitly logged when triggered.

---

## 6. Image Handling (Major Upgrade)

### Input Standard

- Accept images up to **20MB**
- Preserve **full native resolution**
- Typical posters: ~5000px long side @ ~1–5MB

### Derivative Strategy

Original image is preserved and cached per job.

Per-stage derivatives are created **only if required**:

- `OCR_IMAGE_LONG_SIDE_PX` (default: 5000)
- `TRANSLATION_IMAGE_LONG_SIDE_PX` (default: 2000)
- `INPAINT_IMAGE_LONG_SIDE_PX` (default: 2000)

Derivatives are:

- Generated lazily
- Cached per (job_id, stage, long_side_px)
- Logged when created or skipped

Final output always uses original image bytes.

---

## 7. OCR Pipeline (Current State)

### OCR Mode

- Google Vision `DOCUMENT_TEXT_DETECTION`
- Full hierarchy used:
  - pages → blocks → paragraphs → words

### Geometry Model (Upgraded)

Each OCR region may include:

- `bbox_norm` (legacy, axis-aligned)
- `geometry` (optional, preferred):
  - `quad_norm`: 4 normalized vertices (TL, TR, BR, BL)
  - `center_norm`: centroid of quad
  - `angle_deg`: rotation angle (derived from TL→TR vector)

Backward compatible when geometry is absent.

---

## 8. Rotation-Aware Line Reconstruction

### Method

- Extract word-level geometry
- Group words into paragraphs by proximity
- Compute dominant paragraph angle (median, outlier-filtered)
- Rotate word centers into paragraph-aligned space
- Cluster by rotated Y coordinate
- Reconstruct lines with preserved rotation

### Result

- Angled text supported
- Credits lines are readable and spatially coherent
- Much better than naive vertical overlap

### Known Limitation

- “Over / under” credit titles (e.g., role above name) are currently flattened into single lines

This is intentional and sets up the next phase.

---

## 9. OCR Output Contract (Current)

OCR produces **LineRegions** with:

- Text (concatenated words)
- Role (currently `other`)
- Rotation (`angle_deg`)
- Spatial data (`center_norm`, `quad_norm`)
- Suitable for:
  - Debug display
  - Downstream semantic grouping

Translation & inpainting are currently skipped during OCR-focused testing.

---

## 10. What Is Working Well

- Full-res OCR significantly improves small-font accuracy
- Credits blocks are clearly visible in logs
- Names vs. titles show consistent font-height differences
- Logging volume is high-signal, not noisy
- Pipeline is controllable and debuggable

This is a **stable base**.

---

# Appendix A — NEXT TODO (Critical)

## Credits Block Detection & Semantic Grouping

### Problem Statement

Credits blocks require different handling than the rest of the poster:

- Extremely small fonts
- Dense semantic structure
- Mixed content:
  - Proper names (do NOT translate)
  - Titles (“Directed by” → translate)
  - Certifications (“A.C.E.”, “ASC”, “BSC” → do NOT translate)
  - Logos (do NOT translate)
  - Release info (translate selectively)

### Approved Strategy

1. **Detect whether a credits block exists**
2. **Locate its bounding box (may be rotated)**
3. Extract it as a high-resolution sub-image
4. Run a specialized OCR + grouping pass on that region
5. Process remaining poster regions separately

Credits blocks are:

- Almost always near the bottom
- Sometimes also appear as “lite” name-only blocks near the top
- Sometimes include a tiny legal notice at bottom-center

### Grouping Model (Target)

Introduce a higher-level concept:

- **CreditGroup**
  - ProperNameGroup (do not translate)
  - TitleGroup (translate)
  - CertificationGroup (do not translate)
  - LogoGroup (ignore)

Font-height clustering + LLM-based classification may be used.

### Open Design Question

For “over & under” credits:

- Keep as **two stacked bounding boxes** (preferred)
- Or a single multiline group with preserved line breaks

Decision: Lean toward **two boxes** to preserve layout fidelity.

---

## Restart Instructions (IMPORTANT)

When starting a new ChatGPT thread:

1. Upload this `ChatGPT_Control.md`
2. Say:
   > “Resume from Appendix A — Credits Block Detection”
3. State whether the next step is:
   - Vision-based credits block detection
   - Or Cursor prompt generation for implementation

No other context should be required.

---
