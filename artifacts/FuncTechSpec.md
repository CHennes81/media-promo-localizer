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

- **v0.3** – Refined PoC scope to focus on reusable poster templates, per-locale previews, and JSON export (flat image input; PSD/DAM integration and inpainting deferred to future phases).
- **v0.2** – Added stub login requirement, improved processing UX, neutralized project naming, and added per-step timing data to the API response.
- **v0.1** – Initial draft for PoC: scope, architecture, and pipeline defined.

---

## 2. Overview

### 2.1 Problem Statement

Movie and TV studios produce English-language promotional artwork (posters, one-sheets, key art) and then localize it manually for many international markets. The current workflow typically looks like:

- Human translators produce localized copy for each market.
- Human designers remove or hide the original English text from the artwork.
- Designers re-create the localized text using similar fonts, colors, and effects, often from scratch.
- Designers patch any background imagery revealed by repositioned or resized text.
- The same structural decisions (what text goes where, which pieces translate vs stay locked) are re-thought in each market.

This is time-intensive and expensive, causing slower time-to-market and higher localization costs. It also leads to duplicated effort: every territory repeats many of the same structural decisions on the same key art.

There is an opportunity to:

- Do the structural analysis of a poster once (identify text regions, semantics, and policies),
- Reuse that work across many locales,
- And give local teams a strong AI-assisted starting point instead of a blank canvas.

### 2.2 PoC Goal

The Media Promo Localizer PoC demonstrates that AI-driven automation can perform most of the **structural and first-pass localization work** for key art, while leaving final creative control with designers and marketers.

For a single English master poster (flat image):

1. Accept an English promotional poster as input (JPG/PNG; flat image for PoC, PSD in future phases).
2. Automatically detect and read the English text (OCR) and identify its bounding boxes and orientation.
3. Classify each text region by semantic role (e.g., main title, tagline, release message, credits block, rating badge, URL).
4. Apply studio-style policies to decide which regions are localizable vs locked (titles, taglines, release lines, credits roles, URLs, logos, etc.).
5. Let a Marketing Localization Lead review and finalize a reusable **poster template** once per asset:
   - Confirm roles, adjust bounding boxes, and set simple layout constraints.
   - Bounding boxes and coordinates are stored in a **canonical, normalized form** (percentages of image width/height) so they remain valid at any resolution.
6. For one or more target locales, generate AI-assisted localized text for localizable regions and render **per-locale preview images** that:
   - Place localized text where it fits within constraints.
   - Clearly mark “FPO/manual art required” regions where automatic layout is not safe.
7. Export a per-locale package consisting of:
   - A preview JPG/PNG.
   - A localized `PosterTemplate` JSON describing all regions, their final text, and render status.

Local designers and marketers then use these packages to finalize PSDs and deliverables in their existing tools and DAM systems. Future phases may add direct PSD layer manipulation and background inpainting; this PoC stops at high-quality previews and structured template export.

The PoC aims for roughly **80–90 percent automation** of the repetitive structural and first-pass localization work, not complete replacement of human review. Ideally, human effort is focused on final review, polishing, and truly creative adjustments.

### 2.3 Success Criteria (for demo)

For a small set of curated posters:

- The system can ingest **real, high-resolution** poster images:
  - Internally downscaling for OCR/analysis as needed,
  - While preserving and displaying a full-resolution preview to the user.
- Auto-detection and classification of text regions is:
  - Correct or easily fixable for the majority of regions via a single human review pass.
  - Robust enough to handle:
    - Multiple text roles (titles, taglines, release messages, credits blocks, URLs, badges).
    - Angled text and dense credits bands with overlapping elements (logos, URLs, rating boxes).
- A Marketing Localization Lead can:
  - Take a master poster from upload to **published template v1** in a small number of edits.
  - Reuse that template to generate localization packages for several locales without structural rework.
- Per-locale outputs:
  - Contain sensible AI-assisted translations/transcreations for key text (especially taglines and release messages).
  - Produce believable preview images that look like plausible localized key art, with FPO indicators where human art is required.
  - Demonstrate the economic advantage that **template work scales with image count, while localization benefits scale with locale count**.
- The overall demo clearly shows:
  - “We analyze a poster once, then fan out many language-ready variants,”
  - While keeping final creative and legal responsibility firmly in human hands.

---

## 3. Actors & Responsibilities

### 3.1 Global Marketing Lead

- Owns the campaign and decides which key art assets and markets should be localized.
- May define high-level policies (e.g., whether main titles are localized in certain scripts or specific markets).
- Approves which PoC outputs are used as internal demos vs shared with external stakeholders.

### 3.2 Marketing Localization Lead (MLL)

_Primary user of this tool in the PoC._

- Operates the Media Promo Localizer.
- Uploads master artwork and runs auto-tagging.
- Reviews and corrects AI classification of text regions.
- Sets translation/locking policies per region (within the bounds of studio policy).
- Publishes the final **`PosterTemplate`** for each asset.
- Initiates locale runs and exports localization packages.
- Provides feedback on AI performance and where manual intervention is still required.

### 3.3 Local Market Marketers / Creative Teams (outside the tool)

- Receive localized text proposals, previews, and template data from the central team.
- Decide whether to accept, adapt, or ignore AI text suggestions.
- Apply final copy and layout in PSD (or equivalent) tools using their existing workflows.
- Ensure cultural, linguistic, and legal correctness for their market.
- Deliver finished localized artwork back into the studio DAM.

> **Note:** For this PoC, Local Market teams are **conceptual** actors. The tool’s output is designed with them in mind, but they do not directly interact with the system UI.

### 3.4 Legal / Compliance / Rating Bodies (context only)

- Govern rating badges and legal copy (e.g., MPAA/MPA ratings, partner legal language).
- Their requirements are modeled as **policies** and simulated assets in the PoC.
- Actual legal approval workflows and integrations remain **out of scope**.

---

## 4. Artifacts: Inputs & Outputs

### 4.1 Inputs

- **Master key art (flat image)**
  - Format: JPG/PNG.
  - Represents the approved global one-sheet or hero artwork.
  - The system may internally downscale the image to an “analysis resolution” for OCR and layout detection.
  - All bounding boxes and coordinates are stored in a **canonical normalized form**:
    - `x`, `y`, `width`, `height` as percentages of image width/height (0–1),
      so they remain valid at any display resolution.

- **Campaign configuration** (conceptual for PoC)
  - Show/film identifier.
  - List of target locales (e.g., `es-MX`, `fr-FR`, `pt-BR`, `ja-JP`, `ru-RU`, `vi-VN`).
  - Brand rules (simulated in PoC), such as:
    - Which semantic roles are typically localizable vs locked.
    - Script-based title policy (e.g., non-Latin scripts may localize main titles).
    - Placeholders for fonts (e.g., “StandardBillingCondensed”) and legal snippets.

### 4.2 Outputs

- **Master `PosterTemplate` JSON** for the asset:
  - List of **regions**, each with:
    - A unique ID.
    - Normalized bounding box (`x`, `y`, `width`, `height` in 0–1 space).
    - Semantic role (e.g., `MAIN_TITLE`, `AUX_TITLE`, `TAGLINE`, `RELEASE_MESSAGE`, `RELEASE_DATE`,
      `DIRECTOR_PROMO`, `CREDITS_BLOCK`, `RATING_BADGE`, `PARTNER_LEGAL_IMAX`, `URL_MAIN`, `SOCIAL_HANDLE`).
    - Locking / translation policy flags (e.g., `locked`, `localizable`, `fpoOnly`).
    - Layout constraints (e.g., `maxHorizontalExpansionPct`, `minScale`, `maxScale`).
  - Optional grouping constructs:
    - e.g., a logical `CREDITS_BAND` region whose `children` are `CREDITS_BLOCK`, `RATING_BADGE`, `STUDIO_LOGO`, `URL_MAIN`, etc.

- **Per-locale localization packages**:
  - Localized `PosterTemplate` JSON including, per region:
    - The localized text chosen/proposed for that locale.
    - Render status (`OK`, `FPO_OVERFLOW`, `FPO_MANUAL_ONLY`, etc.).
  - Per-locale **preview image** (JPG/PNG) based on the master poster:
    - Localized text drawn where it fits within the region’s constraints.
    - Distinct visual treatment for FPO / manual-art-required regions.

These outputs are designed to “hand off cleanly” to local market teams who continue working in PSD/DAM, even though PSD/DAM integrations are not implemented in the PoC.

---

## 5. Core Principles

1. **Do the structural work once, reuse across many markets**
   - Each key art asset gets a single, reusable `PosterTemplate`.
   - The structural thinking (what is text, what role it plays, what translates vs stays) is done once centrally instead of repeated per locale.

2. **AI assists, humans decide**
   - AI handles:
     - OCR, region detection, role classification.
     - Initial text proposals for target locales.
   - Humans (Marketing Localization Lead + local markets) retain:
     - Final say on region roles and layout constraints.
     - Final copy choices and any nuanced local adaptation.
   - The tool never silently overrides confirmed human decisions.

3. **Policy-driven translation vs locking**
   - Localizability is governed by **explicit policies**, not opaque LLM behavior:
     - e.g., main titles locked by default except in certain scripts/markets.
     - URLs, social handles, logos, and rating badges are locked or DAM-swapped, not translated.
     - Credits roles are localizable while names are preserved.
   - Policies can be tuned over time without changing model behavior.

4. **Normalized geometry for flexible resolution**
   - All bounding boxes and coordinates are stored as normalized percentages of the image size.
   - The same template can be applied to:
     - Internal analysis images (downscaled).
     - High-resolution previews.
     - Future integrations with PSDs or alternate formats.

5. **No risky layout guesses**
   - The system uses simple, conservative rules:
     - Attempt to “cheat wider” within configured limits before scaling font size down.
     - Never move text into fundamentally new image areas or drastically change composition.
   - When text cannot be safely auto-laid out:
     - The region is marked as FPO / manual-art-required.
     - Human designers retain control over complex adjustments.

6. **Respect for legal & partner rules**
   - Rating badges, partner logos, and associated legal copy:
     - Are treated as locked or DAM-sourced elements.
     - Are not free-form translation fields in the PoC.
   - The PoC simulates these behaviors; actual legal systems and approval flows live outside this spec.

---

## 6. End-to-End Workflow (POC)

### 6.1 Stage 1 – Auto-Tag Master Artwork

**Goal:** Produce a draft `PosterTemplate` from a flat master image.

1. **Upload master poster**
   - The Marketing Localization Lead uploads a JPG/PNG for a given campaign asset.
   - The system stores the original at full resolution and creates an internal analysis copy (downscaled if needed).

2. **OCR & region detection**
   - The system runs OCR and object detection over the analysis image to identify:
     - Text regions (lines and blocks), including angled text.
     - Bounding boxes and orientation.
   - Bounding boxes are normalized to `[0, 1]` relative to the image dimensions.

3. **Two-pass analysis of the credits band**
   - **Pass 1:** Detect small discrete elements in the lower band, such as:
     - Rating badges, studio and partner logos.
     - URLs and social handles.
   - **Pass 2:** Using what remains in that band:
     - Identify dense text areas as `CREDITS_BLOCK`.
     - Model these as separate child regions under a logical `CREDITS_BAND`, allowing overlap.

4. **Semantic role classification**
   - Using heuristics + an LLM, the system assigns each detected text region a semantic role, including (but not limited to):
     - `MAIN_TITLE`, `AUX_TITLE`, `TAGLINE`, `RELEASE_MESSAGE`, `RELEASE_DATE`,
       `DIRECTOR_PROMO`, `PRODUCER_PROMO`, `CAST_PROMO`,
       `CREDITS_BLOCK`, `RATING_BADGE`, `PARTNER_LEGAL_IMAX`,
       `URL_MAIN`, `SOCIAL_HANDLE`.
   - The LLM’s job is **role classification only**; it does not decide lock/translate behavior.

5. **Policy application (lock vs localizable)**
   - A policy engine sets initial flags per region:
     - Titles: locked by default (configurable per market/script).
     - Taglines / promo copy: localizable via transcreation.
     - Release lines and dates: localizable with locale-specific formatting rules.
     - URLs / socials / logos / badges: locked or DAM-swapped, not translated.
     - Credits block: roles localizable, names preserved.
   - Layout defaults (e.g., maximum horizontal expansion, minimum scale factor) are set according to role and studio guidelines.

6. **Draft `PosterTemplate` created**
   - The system persists a draft `PosterTemplate v0`:
     - Regions, semantic roles, normalized bounding boxes, lock flags, and layout constraints.

---

### 6.2 Stage 2 – Template Review & Approval

**Goal:** Let the Marketing Localization Lead finalize the template **once per asset**.

1. **Visual review UI**
   - The master poster is displayed at a visually appropriate resolution.
   - Color-coded overlays indicate region types (e.g., localizable vs locked vs FPO-only).
   - Selecting a region reveals its role, bounding box, and policies.

2. **Region edits**
   - The Marketing Localization Lead can:
     - Correct misclassified semantic roles.
     - Adjust normalized bounding boxes (drag/resize) to fine-tune region geometry.
     - Configure layout constraints:
       - Allow/forbid horizontal expansion (`maxHorizontalExpansionPct`).
       - Set min/max font scale factors.
     - Mark regions as FPO-only where automated rendering is not desired.
     - Override initial locked/localizable flags when campaign-specific exceptions apply.

3. **Overlap handling in credits band**
   - The credits band is treated as a logical group containing:
     - `CREDITS_BLOCK`, `RATING_BADGE`, `STUDIO_LOGO`, `PARTNER_LOGO`, `URL_MAIN`, etc.
   - Overlapping bounding boxes are allowed and expected:
     - Each child has its own semantics and lock/translate policy.

4. **Template publication**
   - When the MLL is satisfied, they publish `PosterTemplate v1` for this asset.
   - This is typically a one-time operation:
     - The same template is reused across locales and future runs.
     - Structural auto-tagging is not repeated unless the underlying art changes.

---

### 6.3 Stage 3 – Locale Runs & Export

**Goal:** Use the finalized template to generate AI-assisted localization packages for one or many target locales.

1. **Locale selection**
   - The MLL selects one or more target locales (e.g., `es-MX`, `fr-FR`, `ja-JP`).
   - The system uses the published `PosterTemplate v1` as the structural blueprint.

2. **AI text proposals (per locale)**
   - For each locale and each **localizable** region:
     - Generate direct translations where appropriate (e.g., `RELEASE_MESSAGE`, `RELEASE_DATE`, boilerplate legal where allowed).
     - Generate transcreative variants for taglines and promo copy, aiming to preserve tone and impact over literal wording.
   - Title translation policies (e.g., non-Latin scripts may localize main titles) are respected according to configuration, but local markets retain final authority outside this PoC.

3. **Layout constraint enforcement**
   - For each localized string:
     - The system attempts to place the text within the region’s normalized bounding box.
     - It may:
       - Expand the region horizontally up to `maxHorizontalExpansionPct`.
       - Scale the font down to `minScale` if needed.
     - If the text still cannot fit within safe constraints:
       - The region is marked as `FPO_OVERFLOW` or similar.
       - The preview visually indicates that manual design work is needed.

4. **Export per-locale localization packages**
   - For each locale, the system produces:
     - A **preview image** (JPG/PNG) derived from the master poster:
       - Localized text placed in all `OK` regions.
       - FPO/overflow regions visibly highlighted as needing human art.
     - A **localized `PosterTemplate` JSON** including:
       - Final chosen/proposed text for each region.
       - Render status and any overflow flags.

5. **Handoff to local markets**
   - Local market teams receive:
     - The preview (to understand intent and placement).
     - The localized template (to see exact text and region metadata).
   - They then:
     - Apply final copy and layout in PSD or equivalent tools.
     - Make any necessary creative adjustments.
   - Final PSDs and JPG/PNGs are checked into the studio DAM under existing processes (outside this PoC’s scope).

---

## 7. Out-of-Scope Items (PoC)

To keep the PoC focused and achievable, the following items are explicitly **out of scope** and may be addressed in future phases:

1. **Direct PSD integration**
   - Reading, modifying, or writing Photoshop PSD files.
   - Preserving or editing live text layers, masks, or adjustment layers.
   - Mirroring the exact PSD layer structure in localized outputs.

2. **Background inpainting and complex compositing**
   - Automatically removing existing text from the image and reconstructing detailed background art.
   - Complex compositing operations (e.g., integrating new visual elements beyond text).

3. **Full DAM and Creative Cloud integrations**
   - Direct integration with studio DAM systems.
   - Adobe Creative Cloud / CC Libraries connectors.
   - Automated check-in/check-out or versioning workflows.

4. **Legal, MPA/MPA-style approvals, and partner systems**
   - Automated legal compliance scans beyond simple policy checks.
   - Direct submission to rating boards or partner platforms.
   - Approval status tracking or audit trails.

5. **Advanced layout and design changes**
   - Moving or resizing major non-text visual elements.
   - Advanced typographic effects (curved baselines, complex warps, highly stylized text treatments).
   - Global re-layout of the poster beyond simple bounding-box-based text placement.

6. **Production-grade security and multi-tenant support**
   - Fine-grained access control, roles, and multi-tenant configurations.
   - Hardening for production studio environments (beyond reasonable PoC security hygiene).

The PoC focuses on demonstrating that:

- A single **master structural template** can be created from a poster.
- That template can be reused across many locales.
- AI can meaningfully reduce the repetitive work of text localization and first-pass layout,
  while respecting existing PSD and DAM-centric workflows and keeping humans in control.

---

## 8. Technical Constraints & Assumptions (PoC)

### 8.1 Backend stack

- The backend is implemented in **Python** using **FastAPI** and runs under an ASGI server such as **Uvicorn**.
- All I/O-heavy operations (file handling, simulated pipeline stages) are implemented with **async** functions.
- The backend lives under `apps/api/` and is the only area modified for Sprint 2.

### 8.2 Frontend & API boundary

- The frontend lives under `apps/web/` and communicates exclusively with the backend via HTTP/JSON APIs defined in `artifacts/API_Documentation.md`.
- For this PoC, the frontend is treated as a **trusted client**; no API authentication or authorization is enforced.
- Sprint 2 will make only minimal adjustments to the existing UI:
  - Wire the upload form to `POST /v1/localization-jobs`.
  - Poll `GET /v1/localization-jobs/{jobId}` and show progress/results.
- The full “Template Review” UI (for Marketing Localization Lead adjustments) will be implemented in a later sprint.

### 8.3 File handling

- Input images are **flat** JPG/PNG posters; PSD and multi-layer formats are not supported in this PoC.
- The backend stores the original upload at full resolution on local disk in a temporary area, e.g.:
  - `apps/api/tmp/uploads/{job_id}/poster.{ext}`
- An internal “analysis” copy may be created with a maximum long edge (e.g., `ANALYSIS_MAX_LONG_EDGE_PX = 3072`) for OCR and layout detection.
- Cleanup of temporary files is **best-effort**:
  - Jobs have a configurable TTL after which their files should be deleted.
  - The PoC is not designed for long-term archival of uploads.

### 8.4 Coordinate system

- All region geometry is stored in a **normalized coordinate system** independent of resolution:
  - `x`, `y` represent the **top-left corner** of the bounding box, expressed as fractions of the image width/height in the range `[0.0, 1.0]`.
  - `width`, `height` are the box width/height, also expressed as fractions of the image width/height.
  - `rotation_deg` is an optional numeric field representing **clockwise rotation in degrees** (0° = baseline horizontal).
- Rotation is applied around the **center of the bounding box**, not the top-left corner.
- This allows the same `PosterTemplate` to be applied to:
  - The analysis image,
  - High-resolution previews,
  - Future PSD-based workflows.

### 8.5 Persistence & durability

- Job state is stored in an **in-memory repository** (e.g., a process-local dictionary wrapped by a `JobRepository` abstraction).
- This repository:
  - Is not durable across process restarts.
  - May evict jobs after a configurable TTL (e.g., 1–2 hours) or when a max job count is exceeded.
- Uploaded files are stored on local disk under a temporary path and are subject to the same TTL/eviction rules.
- This design is sufficient for a demo and light public usage but **not** for production workloads.
- The `JobRepository` abstraction is defined so that future implementations (e.g., SQLite/Postgres) can be plugged in without changing API contracts.

### 8.6 Job lifecycle

- All long-running work is modeled as an **asynchronous job**:
  - `POST /v1/localization-jobs` creates a new job and returns a `jobId`.
  - `GET /v1/localization-jobs/{jobId}` returns job status and details.
- Jobs move through a simple lifecycle:
  - `PENDING` → `RUNNING` → `COMPLETED` or `FAILED`.
- Internally, the mock pipeline simulates multiple stages (e.g., upload, OCR, analyze, localize) and records timing per stage.
- The frontend uses a simple **polling** model to track job progress; websockets or server-sent events are out of scope for this PoC.

### 8.7 Non-functional limits

- Max upload size is enforced (e.g., `MAX_UPLOAD_SIZE_MB = 20`); larger uploads are rejected with a clear error.
- Supported MIME types are limited to `image/jpeg` and `image/png`; all others are rejected.
- The system is designed for a **small number of concurrent users** and is not load-tested for high throughput.
- The mock pipeline is tuned for demo responsiveness:
  - Typical job completion under ~10 seconds for reasonably sized posters.
  - Stage timings are simulated within realistic ranges to feel believable, not instantaneous.

### 8.8 Logging & observability

- The backend uses Python’s built-in `logging` module for application logs.
- Log level is controlled via configuration (e.g., `LOG_LEVEL` env var):
  - `DEBUG` for more verbose development output (method entry/exit, key decisions).
  - `INFO` or higher for demo/“prod-ish” deployments.
- At minimum, the system logs:
  - Job creation (jobId, filename, requested locales).
  - Job completion or failure (jobId, status, total duration).
  - Validation and processing errors with appropriate error codes.
- Logs are written to stdout/stderr for capture by the hosting platform (e.g., Railway); structured logging and external log sinks are future enhancements.

### 8.9 Security

- The PoC does **not** implement user authentication or fine-grained authorization.
- It is assumed to run in a controlled environment and/or behind a trusted frontend.
- No secrets (API keys, tokens) are required or used in Sprint 2; `LOCALIZATION_MODE` must remain `mock`.
- Production-grade security (SSO, JWT, role-based access, rate limiting, etc.) is explicitly out of scope and must be added before any real studio deployment or handling of sensitive assets.

### 8.10 Configuration

- Configuration is supplied via environment variables; `.env` files are ignored by git.
- At minimum, the following are supported in Sprint 2:
  - `LOCALIZATION_MODE` (must be `mock`).
  - `MAX_UPLOAD_SIZE_MB` (default 20).
  - `ANALYSIS_MAX_LONG_EDGE_PX` (default e.g., 3072).
  - `JOB_TTL_SECONDS` (default e.g., 7200).
  - `LOG_LEVEL` (default `INFO`).
- Additional configuration (e.g., supported locales list, mock timing ranges) may be introduced in later sprints as needed.

---

## 9. Logging & Observability

### 9.1 Goals

For Sprint 2, logging is primarily for:

- Local debugging during development.
- Basic diagnostics when the PoC is deployed to a shared environment (e.g., Railway).
- Providing enough context to understand failures without attaching a full debugger.

We are **not** building a full observability stack (no distributed tracing, metrics aggregation, or log shipping) in this sprint, but the design should make it easy to add those later.

### 9.2 Logging Approach

- Use Python’s built-in `logging` module, configured in a small `logging_config.py` helper under `apps/api/`.
- Configure a **single application logger** namespace (e.g., `media_promo_localizer`) that all modules inherit from.
- Emit logs in **structured-ish** form (key information as fields in the message), while still using simple text output for PoC.

Example (conceptual, not code):

- `INFO  JobCreated jobId=abc123 targetLang=es-MX fileName=minecraft-us-onesheet.png`
- `INFO  JobUpdated jobId=abc123 stage=OCR status=completed durationMs=842`
- `ERROR JobFailed jobId=abc123 stage=TRANSLATION errorCode=TRANSLATION_MODEL_ERROR`

### 9.3 Log Levels

Recommended levels:

- `DEBUG` – Detailed internal information (e.g., validation branches, intermediate decisions). Only enabled in local/dev.
- `INFO` – High-level lifecycle events:
  - Job created / updated / completed / failed.
  - Backend startup and shutdown.
  - Health checks (at a low frequency).
- `WARNING` – Recoverable anomalies:
  - Suspicious but non-fatal input.
  - File that is technically valid but close to size limits.
- `ERROR` – Request-level failures:
  - Exceptions during processing (caught and mapped to error responses).
- `CRITICAL` – Only for unrecoverable situations:
  - Misconfiguration at startup (e.g., missing env var required for a future live mode).
  - Serious runtime issues that might require a restart.

The **default log level** for the PoC will be `INFO`, with an environment variable (e.g., `LOG_LEVEL=DEBUG`) enabling more verbose output.

### 9.4 Log Fields

Where reasonable, logs should include:

- `jobId` – For any message related to a particular localization job.
- `stage` – One of `upload`, `pipeline_orchestration`, `mock_ocr`, `mock_translation`, `mock_inpainting`, `serialization`.
- `targetLang` – BCP-47 code if applicable.
- `durationMs` – For completed stages or total job duration.
- `errorCode` – When logging an error, mirror the internal error code used in the API error payload.

We don’t need full JSON logs in Sprint 2, but we should keep the **field naming consistent** to enable later adoption of structured logging.

---

## 10. Error Handling & HTTP Semantics

### 10.1 Principles

Error handling should:

1. **Protect implementation details**
   - Never leak low-level stack traces or vendor error messages to the client.
   - Map internal exceptions to clean, documented error codes/messages.

2. **Be predictable**
   - Use a small, well-defined set of HTTP status codes.
   - Use a consistent JSON error envelope.

3. **Be diagnosable**
   - Include error codes and human-readable messages in responses.
   - Log the underlying exception with enough context to debug.

### 10.2 Error Model

All non-2xx responses from the backend will use a **standard error envelope**:

```json
{
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "Human-readable message.",
    "details": {
      "...": "Optional additional fields depending on error type"
    }
  }
}
```

#### 10.2.1 Validation / input errors (`400`)

Examples:

- Missing `targetLanguage`.
- Unsupported file type or corrupted upload (detected at parse-time).
- Invalid `jobId` format.

HTTP status: **400 Bad Request**

Example payload:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "targetLanguage is required.",
    "details": {
      "field": "targetLanguage"
    }
  }
}
```

If multiple validation problems exist, we may include a `problems` array in `details`, but for Sprint 2 a single primary message is sufficient.

#### 10.2.2 Domain errors (`404` / `409`)

Examples:

- `jobId` not found.
- Job exists but is in a terminal failure state and cannot be retried (for a future extension).

HTTP status:

- **404 Not Found** – Job doesn’t exist.
- **409 Conflict** – (Reserved for future behavior changes like retry conflicts).

Example (job not found):

```json
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "Localization job not found."
  }
}
```

#### 10.2.3 Internal / vendor errors (`500`)

Even though Sprint 2 uses a mock engine, we define the shape now to keep the contract stable when Sprint 3 introduces live providers.

Examples:

- Underlying AI provider timeout.
- OCR service throws an unexpected error.
- Inpainting provider returns invalid data.

HTTP status: **500 Internal Server Error**

Example:

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Unexpected error while processing the job."
  }
}
```

Internally, logs should capture the real exception, including provider names, request IDs, and any debugging info that must NOT be sent to the client.

#### 10.2.4 Summary of HTTP Status Codes

- `200 OK` – Successful `GET /v1/localization-jobs/{jobId}` and `GET /health`.
- `202 ACCEPTED` – Successful `POST /v1/localization-jobs` (job created and queued/processing).
- `400 BAD_REQUEST` – Validation or parsing error.
- `404 NOT_FOUND` – Unknown `jobId`.
- `415 UNSUPPORTED_MEDIA_TYPE` – File type not allowed (e.g., non-image).
- `500 INTERNAL_SERVER_ERROR` – Any unexpected internal failure.

#### 10.2.5 Health Response

The health endpoint is intentionally simple and unauthenticated for the PoC.

- **Method:** `GET /health`
- **Status:** `200 OK` (always, unless the process is unhealthy enough to not respond)
- **Body:**

```json
{
  "status": "ok",
  "uptimeSeconds": 1234,
  "version": "0.2.0"
}
```

- `status` – `"ok"` in the PoC; in a more advanced setup, this could reflect deeper readiness checks.
- `uptimeSeconds` – Approximate process uptime (optional but nice for demos).
- `version` – Backend version (aligned with `FuncTechSpec` version).

---

## 11. API Endpoints (Sprint 2)

This section summarizes the endpoints the backend must implement in Sprint 2. The **canonical request/response schemas** remain in `artifacts/API_Documentation.md`; this section defines behavior and relationships.

### 11.1 `POST /v1/localization-jobs`

Create a new localization job.

**Purpose**

- Accept a single poster file upload plus localization parameters.
- Persist a `Job` record (in-memory for the PoC).
- Start asynchronous mock processing of the pipeline stages.
- Return a `jobId` the frontend can use to poll status.

**Behavior**

- Accepts `multipart/form-data`:
  - `file` – image file (JPG/PNG; high resolution allowed).
  - `targetLanguage` – required BCP-47 code (e.g., `es-MX`).
  - `sourceLanguage` – optional (default `en-US`).
- Validates:
  - File presence and non-zero size.
  - Supported MIME type.
  - Allowed maximum size (e.g., 20 MB).
  - Valid `targetLanguage` format.
- On success:
  - Creates a new `jobId`.
  - Stores `Job` record in the in-memory repository with initial status (`queued` / `processing`).
  - Launches asynchronous mock pipeline work.
  - Returns `202 Accepted` with job payload as defined in API docs.

**Error cases**

- Missing or invalid input → `400 INVALID_INPUT`.
- Unsupported file type → `415 UNSUPPORTED_MEDIA_TYPE`.
- Internal failure while creating job → `500 INTERNAL_ERROR`.

### 11.2 `GET /v1/localization-jobs/{jobId}`

Fetch information about an existing localization job.

**Purpose**

- Provide the frontend with the current status of a job.
- When complete, return:
  - Stage timings.
  - Any mock “intermediate insights” (e.g., detected text).
  - URLs/paths or inline data for the localized output image.

**Behavior**

- Looks up job by `jobId`.
- If found:
  - Returns `200 OK` with job payload (status, timestamps, per-stage timings).
  - For completed jobs, includes a reference to the processed image.
- If job is still processing, status will indicate `processing` or the relevant stage and may optionally include a progress estimate.

**Error cases**

- Unknown `jobId` → `404 JOB_NOT_FOUND`.
- Internal lookup error → `500 INTERNAL_ERROR`.

### 11.3 `GET /health`

Simple health/liveness check for the backend.

- Returns `200 OK` with the JSON body described in **10.2.5**.
- No authentication or parameters required.

---

## 12. Testing Strategy

### 12.1 Goals

- Ensure that the core backend behavior is **reliable and repeatable**.
- Demonstrate **mature engineering practices** (unit tests, integration tests).
- Provide a safety net for refactoring, especially when moving from `MockLocalizationEngine` to future live providers.

All tests will use `pytest` and live under `apps/api/tests/`.

### 12.2 Unit Tests

**Targets**

- `LocalizationEngine` implementation (mock):
  - Correct stage sequencing (OCR → translation → inpainting).
  - Correct status transitions (`queued` → `processing` → `completed` / `failed`).
  - Reasonable mock timings.
- Job repository abstraction:
  - Create/read/update semantics.
  - Handling of unknown IDs.
- Request/response validation:
  - Required fields.
  - File type/size checks.
  - Error codes for invalid requests.

**Style**

- Pure unit tests should **not** spin up the FastAPI app.
- They should directly exercise Python classes/functions with in-memory data.

### 12.3 Integration Tests

Integration tests will:

- Use FastAPI’s `TestClient` to run requests against the actual app.
- Exercise:
  - `POST /v1/localization-jobs` end-to-end with a small sample image (fixture).
  - `GET /v1/localization-jobs/{jobId}` polling until job reaches a terminal state.
  - `GET /health` response shape.
- Use the mock engine (no external calls).

Because we simulate async background work, integration tests may:

- Use shorter mock delays in a special `TEST` mode.
- Or bypass delays entirely by injecting a “fast” mock engine in test configuration.

### 12.4 Manual Test Scenarios

For demo readiness, we will maintain a small set of **manual test scenarios**:

- Process each curated poster (e.g., `minecraft`, `the-batman`, `jackass`).
- Verify:
  - End-to-end job creation and completion.
  - Reasonable stage timings.
  - Correct error handling for:
    - Oversized files.
    - Unsupported formats.
    - Invalid `jobId`.

These scenarios can be documented in a separate `artifacts/test/ManualTestPlan.md` if desired (not mandatory for Sprint 2).

### 12.5 CI Integration (Future)

In a future enhancement (outside strict Sprint 2 scope), we can:

- Add a simple CI workflow (GitHub Actions) that:
  - Installs dependencies.
  - Runs `pytest`.
  - Fails on non-zero exit code.
- Optionally enforces:
  - Basic formatting checks (`black`, `ruff`) on the backend code.

---

## 13. Future Extensions (Beyond Sprint 2)

These items are explicitly **out of scope** for Sprint 2 but are anticipated next steps if the PoC is successful.

### 13.1 Live Localization Pipeline (Sprint 3)

- Implement `LiveLocalizationEngine` behind the same interface:
  - Google Vision (or equivalent) for OCR and bounding boxes.
  - Claude (or similar) for translation and cinematic/localized rewrites.
  - Replicate (or similar) for image inpainting.
- Toggle via `LOCALIZATION_MODE=mock|live`.
- Preserve all Sprint 2 API contracts and payload shapes.

### 13.2 PSD-Aware Workflows

- Accept layered PSD input instead of (or in addition to) flat images.
- Parse PSD layer metadata (names, groups, tags) to infer:
  - Titles, taglines, credits, legal text, logos.
- Use PSD coordinates and layer attributes to generate richer templates (e.g., multiple `MAIN_TITLE` segments, per-layer opacity).

### 13.3 Template & Review UI (Marketing Localization Lead)

- Build a dedicated UI for the **Marketing Localization Lead** to:
  - Review AI-detected text regions.
  - Confirm object types (title, tagline, credit block, legal, logo, etc.).
  - Mark objects as locked / localizable / FPO (placeholder).
  - Adjust bounding boxes and constraints (e.g., “can grow left/right”).
- Persist approved templates for reuse across multiple locales.

### 13.4 MPA Compliance Assistance

- Encode key MPAA/MPA marketing rules as a machine-readable checklist.
- Provide an “MPA pre-flight” scan that:
  - Checks presence/position of rating boxes and required legal lines.
  - Highlights possible compliance issues for human review.

### 13.5 Analytics & Insights

- Track aggregate statistics:
  - Jobs per title / per locale.
  - Average automated coverage (% of text auto-localized vs FPO).
  - Time saved compared to manual baselines (if data is available).
- Provide simple dashboards or export hooks to studio BI tools.

### 13.6 Hardening for Production Use

If the PoC evolves into a production system:

- Add authentication and authorization:
  - SSO/JWT, integration with studio identity provider.
- Implement role-based access control:
  - Marketing, Engineering, Vendors, Admins.
- Add rate limiting and abuse protection for public endpoints.
- Replace in-memory storage with a persistent database (e.g., PostgreSQL).
- Introduce real observability:
  - Structured logging.
  - Metrics (e.g., Prometheus).
  - Tracing (e.g., OpenTelemetry).

---

_End of Functional & Technical Specification (Sprint 2 scope)._
