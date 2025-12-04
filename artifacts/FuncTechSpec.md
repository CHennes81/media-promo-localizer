# Media Promo Localizer PoC

## Functional & Technical Specification

---

## 1. Document Metadata

**Project Name:** Media Promo Localizer
**Repo:** `CHennes81/media-promo-localizer`
**Document Path:** `artifacts/spec/FuncTechSpec.md`
**Owner:** Christopher Hennes

### 1.1 Purpose

This document defines the functional and technical specification for the Media Promo Localizer proof-of-concept (PoC) application. It is the primary reference for implementation (via AI-assisted development), review, and future extension.

### 1.2 Audience

- Christopher Hennes (technical lead / product owner)
- AI coding assistants (e.g., Claude) implementing the solution
- Technical reviewers (e.g., studio engineering stakeholders)
- Future maintainers of this codebase

### 1.3 Version History

- **v0.2** – Added stub login requirement, improved processing UX, neutralized project naming, and added per-step timing data to the API response.
- **v0.1** – Initial draft for PoC: scope, architecture, and pipeline defined.

---

## 2. Overview

### 2.1 Problem Statement

Movie and TV studios produce English-language promotional artwork (posters, one-sheets) and then localize them manually for many international markets. The current workflow:

- Human translators produce localized copy.
- Human designers remove the original English text from the artwork.
- Designers re-create the localized text using similar fonts, colors, and effects.
- Designers patch any background imagery revealed by repositioned or resized text.

This is time-intensive and expensive, causing slower time-to-market and higher localization costs.

### 2.2 PoC Goal

The Media Promo Localizer PoC demonstrates that AI-driven automation can perform most of this work end-to-end:

1. Accept a single English promotional poster as input (flat image for PoC, later possibly PSD).
2. Automatically detect and read the English text.
3. Translate the text into one of several target languages.
4. Remove the original text and reconstruct ("inpaint") any newly-exposed background image.
5. Render the translated text back onto the poster in a visually coherent way.
6. Output a localized image suitable for designer review and final polish.

The PoC aims for roughly 80–90 percent automation, not complete replacement of human review. Ideally, human review will be minimize to final review & polishing.

### 2.3 Success Criteria (for demo)

For a small set of curated posters:

- User can upload an English poster and select a target language (FR, ES, JA, KO).
- System returns a localized poster image that:
  - Preserves the original artwork and layout.
  - Replaces English text with translated text in roughly the same locations.
  - Reasonably approximates the original visual style of the text (font family class, weight, size, and color).
  - Produces plausible background fill where original text is removed.
- A designer could plausibly take the output into Photoshop for final polish, rather than starting from scratch.

### 2.4 Non-Goals (PoC Scope Limits)

- Perfect typographic matching of arbitrary proprietary fonts.
- Handling complex 3D or highly stylized title treatments.
- Curved, arced, heavily rotated, or perspective-warped text. (V1 focuses on predominantly horizontal text.)
- Batch processing, job queue management, or multi-user load.
- Production-grade security, auth, and rate limiting.
- Full internationalization nuance (e.g., legal disclaimer variants per territory).

---

## 3. Primary Use Cases

### 3.1 UC-1: Localize a Single Poster

Actor: Studio marketing or localization staff (demo viewer).

Preconditions:

- User can access the web UI.
- Poster image is a flat JPG/PNG at moderate resolution.

Main Flow:

1. User navigates to the Media Promo Localizer page.
2. User uploads a poster image (JPG/PNG).
3. User selects a target language (FR, ES, JA, KO).
4. User clicks Localize Poster.
5. UI shows progress messages such as "Analyzing poster…", "Translating text…", "Rendering localized version…".
6. When complete, UI shows a before/after comparison: original English poster vs localized poster.
7. User may download the localized poster as a PNG.
8. (Optional, post-v1) User may download a layered PSD.

Postconditions:

- Localized poster is available for human designer review and polish.

### 3.2 UC-2: Demo Scenario for Execs

A curated demo flow used in an exec meeting:

1. Load known sample poster A (English).
2. Localize to Spanish and show before/after.
3. Localize to Japanese to demonstrate non-Latin script handling.
4. Explain that the same pipeline can localize to additional languages and integrate with studio asset pipelines.

---

## 4. Constraints and Assumptions

### 4.1 Input Constraints

- Input is a single, flat poster image (JPG/PNG).
- Resolution: arbitrary, but internally we will downscale the long edge to roughly 1600–2500 px for PoC performance.
- Posters used for the demo will have predominantly horizontal text (no complex curves/shapes).

### 4.2 Target Languages

Initial languages:

- French (FR)
- Spanish (ES)
- Japanese (JA)
- Korean (KO)

Future languages (out of scope for v1) may include German, Italian, other target markets as needed

### 4.3 Fonts and Styles

- PoC will not perform automatic font identification.
- Instead, it will use a small set of pre-configured fonts per "text role" (title, tagline, credits), with separate choices for Latin vs CJK scripts.
- Color and style will be approximated based on sampled colors and simple effects (solid fill, optional outline/drop shadow).

### 4.4 Deployment Constraints

- Frontend (React/Vite app) deployed to Cloudflare Pages.
- Backend AI/API service deployed to Railway as a Python web service.
- External ML services (OCR, translation, inpainting) accessed via HTTPS APIs.
- PoC is not expected to handle large concurrent load.

---

## 5. System Architecture

### 5.1 High-Level Components

1. Web Frontend (Cloudflare Pages)
   - React/TypeScript app (based on ai-studio template).
   - Provides the Media Promo Localizer UI.
   - Handles file upload, language selection, progress display, and result viewing.

2. Poster Localization Service (Backend on Railway)
   - Python-based HTTP API (e.g., FastAPI).
   - Exposes REST endpoints for:
     - POST /api/translate-poster – main localization endpoint.
     - GET /health – health check.
   - Implements the localization pipeline (OCR → translation → inpainting → rendering → export).

3. External Services
   - OCR Provider – Cloud OCR (e.g., Google Vision or Azure Read) for text detection and bounding boxes.
   - Translation Provider – LLM-based translator (OpenAI) with prompts tuned for poster copy and credits.
   - Inpainting Model – Image inpainting (e.g., LaMa) hosted via a model-serving platform (e.g., Replicate or similar).

### 5.2 Data Flow (Request Lifecycle)

1. User uploads poster and selects language in the frontend.
2. Frontend sends a multipart/form-data POST request with image plus target language to backend /api/translate-poster.
3. Backend:
   - Validates inputs.
   - Downscales the image to a working resolution.
   - Calls OCR provider to obtain text blocks and bounding boxes.
   - Classifies blocks into text roles (title, tagline, credits, other).
   - Sends grouped text blocks to translation provider (batched), with different prompts for body vs credits.
   - Builds a text mask covering the bounding boxes of all text regions.
   - Calls inpainting model with original image plus mask to remove text and reconstruct background.
   - Renders translated text back onto the inpainted background using role-based fonts and layout.
   - Optionally builds a layered PSD.
   - Returns a response containing a localized PNG (as base64 or URL) and optional metadata about text blocks.

4. Frontend receives response and updates the UI with before/after preview and download links.

### 5.3 Architecture Style

- Backend: Modular, step-based pipeline pattern.
- Service integrations: Strategy pattern via abstract client interfaces for OCR, translation, and inpainting.
- Frontend: Single-page flow for this PoC, using component-based composition.

---

## 6. API Design (Backend)

### 6.1 POST /api/translate-poster

Description:
Main entry point for localizing a single poster image into one target language.

Request (multipart/form-data):

- file (required): Poster image binary (JPG/PNG).
- target_language (required): String enum: fr, es, ja, ko.
- poster_id (optional): String identifier for known posters (used for per-poster style configs in future).

Response (JSON):

    {
      "status": "success",
      "target_language": "es",
      "localized_image": {
        "format": "png",
        "data": "<base64-encoded PNG>"
      },
      "metadata": {
        "original_width": 2000,
        "original_height": 3000,
        "working_width": 1600,
        "working_height": 2400,
        "text_blocks": [
          {
            "id": "title-1",
            "role": "title",
            "source_text": "STAR HEROES",
            "translated_text": "HÉROES ESTELARES",
            "bbox": [100, 200, 900, 300]
          }
        ]
      }
      "timings": {
        "total_ms": 8423,
        "steps": {
          "load_normalize_ms": 35,
          "ocr_ms": 1290,
          "translation_ms": 2150,
          "inpainting_ms": 3670,
          "render_ms": 980,
          "export_ms": 298
        }
      }
    }

Notes:

- For v1, returning localized_image as a base64 string is acceptable. Later, this may become a signed URL to storage (e.g., S3).
- metadata.text_blocks assists debugging and future UI overlays, but the frontend does not need to rely on it for the basic demo.
- The `timings` field provides coarse-grained performance data for the request.
  - `total_ms` is the approximate end-to-end duration of the pipeline for this poster.
  - `steps` contains per-step timings for key pipeline phases: image normalization, OCR, translation, inpainting, text rendering, and export.
- These timing values are intended for **demo and benchmarking** purposes and do not require millisecond-perfect accuracy; simple timestamp difference measurements before and after each step are sufficient.

### 6.2 GET /health

Description:
Simple health check endpoint for monitoring and deployment validation.

Response:

    { "status": "ok" }

---

## 7. Localization Pipeline

The backend implements a linear pipeline of named steps. Each step takes a shared PipelineContext and returns an updated context or raises an error.

### 7.1 Pipeline Steps (Logical)

1. Step 1 – Load and Normalize Image
   - Input: Raw image bytes.
   - Actions: validate file type, decode image, compute working resolution, downscale if needed.
   - Output: Normalized image in context.image_working and original dimensions in metadata.

2. Step 2 – OCR and Text Block Detection
   - Input: context.image_working.
   - Actions: call OCR provider and extract text blocks with bounding boxes, orientation, and confidence.
   - Output: context.text_blocks_raw.

3. Step 3 – Text Role Classification and Grouping
   - Input: context.text_blocks_raw.
   - Actions: heuristically classify blocks as title, tagline, credits, or other based on size and position; optionally group adjacent blocks.
   - Output: context.text_blocks with role and grouping info.

4. Step 4 – Translation
   - Input: context.text_blocks and target language.
   - Actions: batch text blocks by role, call translation provider (LLM) with strict instructions not to translate names in credits and to preserve approximate line structure.
   - Output: updated context.text_blocks with translated_text filled in.

5. Step 5 – Text Mask Generation and Inpainting
   - Input: context.text_blocks and context.image_working.
   - Actions: build a binary mask covering the bounding boxes of all text blocks, call inpainting model with original image plus mask.
   - Output: context.image_background (working-resolution image with text removed and background reconstructed).

6. Step 6 – Text Layout and Rendering
   - Input: context.image_background, context.text_blocks, target language.
   - Actions: map text roles and languages to font families and base styles; for each text block, determine a text layout area based on the original bbox; fit translated text into the area by adjusting font size and line wrapping; render text onto a transparent layer or directly onto image_background.
   - Output: context.image_localized_working (working-resolution localized poster).

7. Step 7 – Export and Scaling
   - Input: context.image_localized_working.
   - Actions: optionally upscale back towards the original resolution via resampling; encode localized image to PNG; (future) generate layered PSD with background and text layers.
   - Output: context.localized_png_bytes, optional context.localized_psd_bytes.

### 7.2 Pipeline Implementation Pattern

- Use a small Pipeline class that maintains ordered steps.
- Each step implements a run(context) method and has a name (e.g., OCR, TRANSLATION).
- This structure allows future agentic behavior (conditional steps, retries, human-in-the-loop) without changing the core model.

---

## 8. Backend Components and Interfaces

### 8.1 API Layer

- Framework: FastAPI (or similar modern Python web framework).
- Responsibilities: HTTP request parsing and validation, invoking the pipeline, mapping outputs to HTTP responses, and converting exceptions into structured error responses.

### 8.2 Pipeline Orchestrator

- Module: poster_localizer.pipeline (example name).
- Responsibilities: own the PipelineContext data structure, define the ordered list of steps, coordinate execution, logging, and error propagation.

### 8.3 External Service Clients

Each external dependency will have its own client interface with at least one concrete implementation.

1. OCR Client
   - Interface: IOcrClient with a method like recognize_text(image) -> List[TextBlockRaw].
   - Implementation: CloudOcrClient using Google Vision or Azure Read.
   - Handles HTTP calls, auth credentials, and error mapping.

2. Translation Client
   - Interface: ITranslationClient with a method like translate(blocks, target_language, mode) -> List[TextBlock].
   - Implementation: LlmTranslationClient using OpenAI.
   - Handles prompt construction, response parsing, and name-preservation behavior.

3. Inpainting Client
   - Interface: IInpaintingClient with a method like inpaint(image, mask) -> image.
   - Implementation: LamaInpaintingClient calling a hosted LaMa model.

### 8.4 Rendering Engine

- Responsibilities: map text roles and languages to font families and styles, perform basic text layout inside bounding boxes, render text onto images (using PIL or similar).

### 8.5 Exporters

- PngExporter – encodes the final image as PNG bytes.
- PsdExporter (future or extended scope) – constructs a PSD with background plus text layers.

### 8.6 Configuration and Secrets

- Use environment variables for OCR API keys and endpoints, OpenAI API key, and inpainting service URL and auth.
- Keep configuration centralized in a config module, not scattered.

---

## 9. Frontend Requirements (Web App)

### 9.1 Authentication (Stubbed for PoC)

For this PoC, the application will include a simple **Login view** to demonstrate that authentication and access control are part of the expected UX, even though no real security will be implemented yet.

Requirements:

- Provide a dedicated **Login screen** with:
  - Email field (text input)
  - Password field (password input)
  - “Log in” button
- Any non-empty email and password combination is treated as valid.
- On successful login:
  - Store a simple “logged in” flag (e.g., in React state and/or localStorage).
  - Route the user to the main **Poster Localizer** page.
- The Poster Localizer page should be inaccessible (via normal navigation) until the user has “logged in”. A simple client-side check is sufficient for this PoC.

The spec must clearly note that:

- This is a **stub implementation** intended only for demonstration.
- In a production deployment, this view would be replaced by real authentication and authorization (e.g., studio SSO / identity provider).

### 9.2 Poster Localizer Page

New feature page in the React app, e.g., /poster-localizer.

Responsibilities:

- File upload (poster image).
- Target language selection (FR/ES/JA/KO).
- Trigger localization request.
- Display progress messages while waiting.
- Display original vs localized image once complete.
- Offer download of localized PNG.

### 9.3 UI Flow

1. Landing section with short description and Upload button.
2. Once file is chosen, user selects target language from a dropdown.
3. User clicks Localize Poster.
4. Frontend transitions to a Processing state: shows a sequence of textual progress messages while awaiting the backend response.
5. Upon success: shows side-by-side view of Original vs Localized and a Download PNG button.
6. Upon error: shows a friendly error message and suggests trying again.

#### 9.3.1 Processing State/Status

While the backend is processing the poster, the UI **must not** remain static. Instead, it should present:

- A visible **animated indicator** (e.g., spinner or progress bar), and
- A sequence of short **status messages** that communicate high-level pipeline phases, such as:
  1. “Analyzing poster…”
  2. “Translating text…”
  3. “Reconstructing background…”
  4. “Rendering localized version…”

For v1 of the PoC:

- It is acceptable for these phases to be **simulated entirely in the frontend** during a single API call (e.g., timed updates to the message every few seconds) rather than driven by real-time server events.
- The primary goal is to ensure that during potentially long-running processing (tens of seconds to a couple of minutes), the user sees visible progress and understands that the system is working through multiple intelligent steps.

Later versions may replace this simulated sequence with actual step-aware progress updates from the backend (e.g., via polling or WebSockets).

### 9.4 API Integration (Frontend)

- Frontend will call the backend at a configurable base URL (e.g., VITE_API_BASE_URL).
- Use fetch or a lightweight HTTP client to send a multipart POST request with file and target_language.
- Expect JSON response with localized_image.data (base64) and basic metadata.
- Convert base64 back to a Blob for display and download.

### 9.5 Branding

- Light, professional styling as Media Promo Localizer.
- No real-world studio branding.
- Optional fictitious logo or wordmark.

---

## 10. Translation Behavior

### 10.1 General Principles

- Use LLM-based translation to allow nuanced control over tone and preservation of names.
- Translation must be deterministic enough for a demo; avoid random creative rewrites.

### 10.2 Credits Handling

- For blocks identified as credits, translate role words (“Directed by”) and prepositions, but do not translate person or company names.
- Preserve overall line structure; names remain in Latin script.

### 10.3 Batching

- Text blocks should be passed to the LLM in batches with explicit IDs.
- LLM output should be requested in a structured JSON-like format to map translations back to blocks.

### 10.4 Prompts

- Prompt templates and rules will be defined separately.
- Implementers must ensure different prompts for body/tagline vs credits, with clear instructions for name preservation and format.

---

## 11. Testing and Quality

### 11.1 Unit Tests

- At minimum, unit tests for text role classification heuristics, bounding box scaling/layout calculations, and prompt-building logic.

### 11.2 Integration and Smoke Tests

- A simple pipeline smoke test using mocked OCR/translation/inpainting clients to ensure pipeline produces a non-empty localized image and no unhandled exceptions for a basic test poster.

### 11.3 Manual QA Checklist

For each curated demo poster:

- Verify localization works in all four languages.
- Verify credits names remain unchanged.
- Verify localized PNG downloads and opens correctly.
- Verify UI does not hang; progress messages appear while processing.

---

## 12. Logging and Observability (PoC Level)

- Backend should log request start/end for /api/translate-poster, key pipeline step transitions, and errors with sufficient context but without sensitive data.
- No full observability stack is required for the PoC, but logs should make it easy to debug failures.
- In addition to writing basic logs, the backend records simple per-step timing metrics for each call to `/api/translate-poster`. These timings are returned to the caller in the `timings` object (see Section 6.1) so that demo users and technical reviewers can understand where time is being spent in the pipeline. No persistent metrics store is required for this PoC; in a production environment, these timings could be exported to a monitoring system for aggregation and alerting.

---

## 13. Future Expansion (Beyond PoC)

Not implemented in v1, but the architecture should allow:

- Layered PSD input instead of flat PNG/JPG, eliminating the need for inpainting.
- More advanced typographic effects (arcs, perspective text).
- Per-title style configuration from the studio’s design teams.
- Batch processing and job queue management for multiple posters.
- Real progress reporting via asynchronous jobs and job status endpoints.
- Integration into internal studio asset-management pipelines.

---

## 14. Risks and Limitations

- OCR accuracy may be imperfect on stylized or low-contrast text.
- Inpainting artifacts may be noticeable in complex backgrounds.
- Font/style approximations may not meet final theatrical marketing standards without human polish.
- LLM translation may occasionally produce inappropriate or off-tone phrases; human review remains required.

---

## 15. Implementation Notes for AI Assistants

- Treat this document as authoritative for design and behavior.
- Do not invent new endpoints, major features, or architectural patterns without explicit instruction.
- Favor clear, modular code that reflects the pipeline and client abstractions described here.
- Keep configuration and secrets externalized (environment variables), not hard-coded.
- Use this spec together with Coding Standards and Sprint Plan artifacts as the combined source of truth.
