You are acting as a senior engineer working in the `media-promo-localizer` repo.

Operate in **IMPLEMENTATION_MODE**:

- You may modify application code and add tests.
- You may NOT modify existing test expectations unless explicitly required by the spec and clearly called out.
- If existing tests fail, assume the implementation is wrong unless the spec clearly contradicts the tests.

---

## Context & control docs

This project is the **Media Promo Localizer** PoC:

- Frontend: React/Vite/TypeScript under `apps/web/`.
- Backend: FastAPI under `apps/api/` with:
  - `/health`
  - `/v1/localization-jobs` POST + GET
  - A mock pipeline (`mock_engine`) simulating OCR / translation / inpainting.
- GitHub CI is currently green; do not break it.

Before making any changes, **open and read** these control docs under `/artifacts`:

1. `ControlDocsInfo.md`
2. `FuncTechSpec.md`
3. `API_Definition.md`
4. `DevProcess.md`
5. `CodingStandards.md`
6. `DevPlan.md` (skim §0–3, especially Sprint 3 description)
7. `DevChecklist_Sprint2.md` (just to understand what was done in Sprint 2)
8. `DevProgress.md` (skim entries to see recent work)

Important constraints and patterns (from the control docs):

- **Spec-first**: Behavior must match `FuncTechSpec.md` and `API_Definition.md`.
- **Pipeline pattern**:
  - Use a `PipelineContext` object passed through small, focused steps (`run(context)`).
  - Use interface-style clients: `IOcrClient`, `ITranslationClient`, `IInpaintingClient` living under `clients/`.
- **Config**:
  - Use env vars for secrets and provider config.
  - Provide a central config module for environment variables (OCR API keys, OpenAI key, etc.).
- **Out-of-scope (for PoC)**:
  - Full background inpainting / complex compositing is explicitly out-of-scope right now.
  - For this batch, we will **prepare** the inpainting interface but NOT implement real background removal.

Subfolders under `/artifacts` are **historical** unless explicitly referenced. Do not modify any artifact file except `DevProgress.md` if instructed.

---

## Task: Sprint 3 – Batch 1: Live pipeline with real OCR + translation

### Goal

Implement the **first real pipeline path** for localization jobs, using **real OCR + translation providers**, while keeping the mock pipeline as the default.

You are implementing **Sprint 3 – Batch 1** only:

- Focus on:
  - Real OCR client (cloud provider or OSS client wrapped behind an interface).
  - Real translation/localization via an LLM (e.g., OpenAI).
  - A `LiveLocalizationEngine` (or equivalent) wired into the existing job pipeline.
  - A configuration switch to choose between mock vs live pipeline.
- Do **not** implement full background inpainting yet; keep `IInpaintingClient` as a stub.

The `/v1/localization-jobs` API surface and response schema **must remain exactly as defined** in `API_Definition.md`. You are only changing the implementation behind that surface.

---

## High-level design

1. **Inspect existing backend structure**:
   - Locate the FastAPI app, routers, and the current mock pipeline (`mock_engine` or equivalent).
   - Identify:
     - Where jobs are created.
     - Where pipeline steps are invoked.
     - Where timings and status are populated.

2. **Introduce provider-agnostic client interfaces** (if not already defined):
   - Under a suitable package (e.g., `apps/api/.../clients/`), define:
     - `IOcrClient` with a method like:
       - `async def recognize_text(self, image_bytes: bytes) -> OcrResult: ...`
     - `ITranslationClient` with a method like:
       - `async def translate_text_regions(self, regions: list[TextRegion], target_locale: str) -> list[TranslatedRegion]: ...`
     - `IInpaintingClient` interface only, but for this batch you will provide a **stub implementation** (no real background removal).
   - Types such as `OcrResult`, `TextRegion`, `TranslatedRegion`, or similar must align with the internal pipeline structures already in use (consult existing models / pipeline code; do NOT invent incompatible shapes).

3. **Real OCR client implementation (Batch 1 scope)**:
   - Implement a concrete OCR client (e.g., `CloudOcrClient`) behind `IOcrClient`.
   - Configuration:
     - Read OCR provider configuration from environment variables in a central config module, e.g.:
       - `OCR_PROVIDER`
       - `OCR_API_KEY`
       - `OCR_API_ENDPOINT`
     - Do not hard-code secrets or project IDs.
   - The implementation should:
     - Accept the uploaded poster image (JPG/PNG) as bytes.
     - Call the OCR provider and normalize the results into your internal `OcrResult` / `TextRegion` structures (bounding boxes, text content, orientation if available).
     - Handle provider errors gracefully:
       - Log a clear message (no secrets).
       - Raise a well-defined exception that the pipeline can catch and translate into an error status per `API_Definition.md`.
   - Tests must **mock** external calls; do not make real network calls during tests.

4. **Real translation client implementation (Batch 1 scope)**:
   - Implement `LlmTranslationClient` (or similar) behind `ITranslationClient`, using an LLM API such as OpenAI.
   - Configuration:
     - Use environment variables:
       - `OPENAI_API_KEY`
       - Optional `TRANSLATION_MODEL` (e.g., `gpt-4o`).
   - Behavior:
     - Take the recognized text regions and the requested target locale (e.g., "fr-FR").
     - Build prompts according to the behavior in `FuncTechSpec.md`:
       - Respect semantics / roles where relevant.
       - Produce localized text while preserving structure.
     - Return translated regions in a structure compatible with the existing pipeline (do NOT change the public API schema).
   - Again, tests must mock the LLM client; no real calls in test runs.

5. **Introduce a LiveLocalizationEngine**:
   - Create a new pipeline implementation, e.g. `live_engine.py`:
     - Uses `IOcrClient` and `ITranslationClient` (and the stub `IInpaintingClient`) to perform a real end-to-end job.
     - Follows the same step-based pattern as the mock engine:
       - Load/validate input.
       - OCR step.
       - Role classification + policy step (reusing existing logic where possible).
       - Translation step.
       - (Placeholder) inpainting step – for now, this should:
         - Either no-op or simply reuse the original image as the “output image” and rely on JSON/template output.
         - Clearly document in code comments that background removal is deferred per `FuncTechSpec` “Out-of-scope” section.
   - Ensure the engine populates the `timings` object in the response per the spec:
     - Measure actual durations for OCR and translation.
     - For the stub inpainting step, it’s fine to report a small timing value or zero with a comment that it is a placeholder.

6. **Configuration: mock vs live mode**:
   - Add a configuration flag (environment-driven), e.g. `LOCALIZATION_MODE` with values:
     - `mock` (default)
     - `live`
   - In the job orchestration layer, use this flag to choose between:
     - Existing mock pipeline (current behavior).
     - New `LiveLocalizationEngine` (real OCR + translation).
   - Preserve existing behavior when `LOCALIZATION_MODE` is not set (treat as `mock` to avoid breaking CI or local dev for other users).

7. **API integration**:
   - Keep the `/v1/localization-jobs` endpoint request/response exactly as defined in `API_Definition.md`.
   - When in live mode:
     - Use the real pipeline to populate the same fields (including text regions, localized text, timings, and any preview/template metadata already defined).
   - Ensure that errors from external services are converted into the appropriate error responses or job failure states per the spec.

8. **Testing & validation**:
   - Add targeted tests for:
     - The new OCR client abstraction (with mocked provider responses).
     - The translation client abstraction (with mocked LLM responses).
     - The LiveLocalizationEngine pipeline, using fully mocked clients to simulate happy path and failure scenarios.
   - Do not modify existing tests unless they are clearly incompatible with the **spec** and new code; if you must change them, do so sparingly and explain why.
   - Run the full backend test suite and ensure everything passes before declaring the batch complete.

9. **DevProgress entry**:
   - After completing the work, append a new entry at the bottom of `artifacts/DevProgress.md` following the documented format, e.g.:

     ```markdown
     ### 2025-12-11 – [Sprint 3] implement live pipeline batch 1 (ocr + translation)

     - Mode: IMPLEMENTATION_MODE
     - Initiator: Cursor / Claude
     - Summary:
       - Added provider-agnostic interfaces for OCR, translation, and inpainting.
       - Implemented real OCR and LLM translation clients behind those interfaces.
       - Introduced a LiveLocalizationEngine and `LOCALIZATION_MODE` config to select mock vs live pipeline.
       - Kept inpainting as a stub per FuncTechSpec out-of-scope; prepared interfaces for future extension.
     - Files touched (high level):
       - (List key backend modules, clients, config, and tests here)
     - Tests:
       - pytest (pass)
     - Outcome: completed
     - Notes:
       - Inpainting is still stubbed; future batch can implement actual background removal once spec is updated.
     ```

---

## Deliverables

When you’re done, provide in your final response:

1. A short summary of the changes made.
2. The list of main files created/modified.
3. Commands you ran to validate (e.g., `pytest`, `uvicorn` dev command if applicable).
4. Any follow-up questions or caveats (e.g., configuration steps Chris must perform to use real providers).
