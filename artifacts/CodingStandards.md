# Coding Standards – Media Promo Localizer

**Location:** `artifacts/coding/CodingStandards.md`  
**Applies to:** This repository (frontend, backend, scripts, tests)

These standards exist so that:

- The codebase looks like it was written by a **cohesive senior team**.
- AI coding assistants (e.g., Claude, ChatGPT) have **clear rails** to follow.
- AI & human contributors can **follow the exact same rules** so that the codebase is **uniform & consistent**.
- Reviewers can skim the repo and immediately see **discipline and consistency**.

This document complements the **FuncTechSpec** and any **DevProcess** / workflow docs.  
The spec defines _what_ to build; this defines _how_ it should look in code.

---

## 1. General Principles

1. **Spec-driven development**
   - Treat `artifacts/FuncTechSpec.md` as the source of truth for behavior.
   - Do not invent new endpoints, features, or flows without explicit direction.
   - When in doubt, prefer **simpler implementations** that clearly match the spec.

2. **Readability over cleverness**
   - Favor clear, explicit code over “smart” one-liners.
   - Assume future readers are tired and under time pressure.

3. **Single responsibility & modularity**
   - Functions and components should do **one thing well**.
   - Break complex logic into smaller units with clear names.

4. **Consistency over personal style**
   - Follow these standards even if your personal preferences differ.
   - Inconsistent style is more damaging than a style you disagree with.

5. **Avoid premature abstraction**
   - Only introduce abstractions (base classes, shared hooks, etc.) when
     - There are at least 2–3 actual call sites, and
     - The shared concept is clear and stable.

---

## 2. Git & Commit Rules

1. **Conventional Commits**
   - Use the form: `type: short summary`
   - `type` must be lowercase; allowed types include:
     - `feat` – new feature
     - `fix` – bugfix
     - `docs` – documentation-only changes
     - `chore` – tooling, config, maintenance
     - `refactor` – internal refactors (no behavior change)
     - `test` – add or update tests
     - `ci` – CI/CD pipeline changes
   - The **summary must be all lowercase** and not sentence-case, start-case, or PascalCase, e.g.:
     - ✅ `feat: add poster upload form`
     - ✅ `docs: update functechspec to v0.2`
     - ❌ `Docs: Add FuncTechSpec v0.2`

2. **Commit scope**
   - Keep commits **small and focused**.
   - A single commit should represent one logical change or small group of closely related changes.

3. **Artifacts and configs**
   - Do not modify Husky, CI configs, or artifacts (spec, coding standards, process docs) unless explicitly asked.
   - When artifacts are updated, use `docs:` type commits.

---

## 3. Frontend Standards (React / TypeScript)

### 3.1 Technology Stack

- React (functional components) with hooks.
- TypeScript for all application code.
- Vite as the build tool.
- CSS-in-JS or modules as already used in the repo (follow existing pattern).

### 3.2 File Organization

- Place React components under `apps/web/src/` in a sensible folder structure (e.g., `components/`, `pages/`, `features/`).
- Keep filenames descriptive and consistent:
  - Components: `PascalCase.tsx` (e.g., `PosterLocalizerPage.tsx`)
  - Hooks: `useSomething.ts`
  - Utility modules: `somethingUtils.ts`

### 3.3 TypeScript & React Best Practices

1. **Strict typing**
   - Avoid `any` unless there is no reasonable alternative and add a comment explaining why.
   - Define `type` or `interface` for props and domain entities.
   - Prefer `interface` for object shapes that may be extended, `type` for unions/aliases.

2. **Functional components with hooks**
   - Use `function ComponentName()` over arrow functions for components for consistent stack traces.
   - Extract complex logic into custom hooks (`usePosterUpload`, `useLocalizationRequest`, etc.).

3. **Props & state**
   - Keep components small; pass only the props they need.
   - Avoid deeply nested prop-passing; consider context or custom hooks where appropriate.

4. **Error handling in UI**
   - Show clear, user-facing error messages when API calls fail.
   - Do not swallow errors silently; log them to console in development.

5. **API integration**
   - Centralize API calls in a dedicated module or hook (e.g., `apiClient.ts` or `usePosterLocalizationApi.ts`).
   - Use TypeScript types for request/response payloads.
   - Do not hardcode API base URLs; use environment variables (e.g., `VITE_API_BASE_URL`).

### 3.4 Styling & UX

1. **Simplicity and clarity**
   - Clean, professional look; no overly flashy effects.
   - Maintain accessible contrast where possible.

2. **Loading / processing states**
   - For long-running operations, always show:
     - An animated indicator (spinner, progress bar), and
     - Status messages (e.g., “Analyzing poster…”, “Translating text…”).

3. **Forms**
   - Validate required fields on the client where reasonable.
   - Avoid throwing raw errors at the user; map to friendly messages.

4. **Accessibility**
   - Use semantic HTML where practical (`<button>`, `<label>`, etc.).
   - Ensure interactive elements are keyboard accessible.

### 3.5 Testing (Frontend)

- Prefer React Testing Library for component tests.
- At minimum, test:
  - The presence of critical UI elements (upload, language select, Localize button).
  - Basic happy-path flows (e.g., “when API returns success, localized image is shown”).

---

## 4. Backend Standards (Python / FastAPI)

### 4.1 Technology Stack

- Python 3.x (matching the repo’s configured version).
- FastAPI (or similar modern framework) for HTTP API.
- `pydantic` for request/response models where appropriate.

### 4.2 Project Structure

- Group backend code under a clear top-level package, e.g., `poster_localizer/`.
- Suggested internal structure:
  - `api/` – FastAPI route definitions.
  - `pipeline/` – pipeline orchestrator and steps.
  - `clients/` – external service clients (OCR, translation, inpainting).
  - `models/` – domain models, pydantic schemas.
  - `config/` – configuration loading and environment variables.
  - `utils/` – small utility functions with no external dependencies.

### 4.3 Code Style

1. **PEP 8 compliant**
   - Standard Python style rules apply (line length within reason; readability first).

2. **Naming**
   - Modules, packages: `snake_case`.
   - Classes: `PascalCase`.
   - Functions & methods: `snake_case`.
   - Constants: `UPPER_SNAKE_CASE`.

3. **Type hints**
   - Use type hints for function parameters and return types.
   - Use `typing` (`List`, `Dict`, `Optional`, `Union`, etc.) as needed.

4. **Formatting & linting**
   - Prefer a standard formatter (e.g., black) and linter (e.g., ruff or flake8) if configured in the repo.
   - Do not fight the autoformatter; let it standardize code layout.

### 4.4 FastAPI & API Design

1. **Routing**
   - Group routes logically (e.g., `translate_poster` in a poster-related router).
   - Use clear and descriptive endpoint paths: `/api/translate-poster`, `/health`.

2. **Models**
   - Define request and response models as pydantic classes when they have structure.
   - Keep them in a `models/` or `schemas/` module, not embedded inline in route functions.

3. **Error handling**
   - Use FastAPI’s `HTTPException` for expected error cases (e.g., bad input, unsupported file type).
   - For unexpected exceptions, log and return a generic 500 error message; do not expose stack traces or internal details in responses.

4. **Configuration**
   - Use environment variables for:
     - OCR API keys and endpoints.
     - OpenAI API key.
     - Inpainting service URL and auth.
   - Provide a central `config` module that reads environment variables and validates required fields early at startup.

### 4.5 Pipeline Implementation

1. **Pipeline context**
   - Use a `PipelineContext` data structure to pass state between steps.
   - This object should be well-typed and documented (fields grouped logically).

2. **Steps**
   - Each step should be a small class or function with a clear `run(context)` method.
   - Steps should not perform side effects unrelated to their responsibility (e.g., the OCR step should not also handle translation).

3. **External clients**
   - Use interface-style classes (`IOcrClient`, `ITranslationClient`, `IInpaintingClient`) to abstract service providers.
   - Concrete implementations (e.g., `CloudOcrClient`, `LlmTranslationClient`, `LamaInpaintingClient`) live in `clients/`.
   - Avoid hardcoding provider-specific details in pipeline steps; call through the interfaces.

4. **Timing**
   - Measure step timings using simple timestamp differences.
   - Populate the `timings` object in the API response as described in the spec.

### 4.6 Testing (Backend)

- Use `pytest` as the test runner.
- At minimum, cover:
  - `PipelineContext` and simple pipeline flow with mocked clients.
  - Text role classification heuristics.
  - Prompt-building and translation mapping logic.

---

## 5. Error Handling & Logging

1. **Error handling**
   - Prefer explicit checks and clear error messages for expected failure modes (bad input, missing file, unsupported mime type).
   - Do not let unexpected exceptions crash the process without logging; catch at an appropriate boundary and log.

2. **Logging**
   - Log:
     - Start and end of `/api/translate-poster` calls.
     - Failures from external services (OCR/translation/inpainting).
     - Pipeline step transitions if helpful for debugging.
   - Avoid logging full image data or API keys; log identifiers and high-level details only.

3. **User-facing errors**
   - In the frontend, always display a user-friendly message if the API request fails.
   - Optionally include a generic “If this persists, contact support” note for future integration.

---

## 6. Dependencies & Configuration Management

1. **Dependencies**
   - Only add dependencies when necessary; prefer the existing stack.
   - Do not add heavy or overlapping libraries for problems already solved by existing dependencies.

2. **Configuration**
   - Use environment variables for secrets and environment-specific settings.
   - Do not commit secrets, API keys, or passwords to the repo.

3. **Environment parity**
   - Keep dev and production configurations as similar as practical, differing mainly in secrets and URLs.

---

## 7. Documentation Expectations

1. **Inline documentation**
   - Public functions and classes should have docstrings or comments that explain their purpose.
   - Complex logic and non-obvious decisions should be documented.

2. **High-level docs**
   - Keep `README.md` up to date with setup instructions and project description.
   - Update the spec and coding standards when higher-level design decisions change.

3. **AI assistant usage**
   - When AI-generated code is added, ensure it is reviewed for:
     - Correctness against the spec.
     - Consistency with these standards.
     - Clarity and maintainability.

---

## 8. Things AI Assistants Must Not Do

To keep the repo coherent and trustworthy, AI assistants must **avoid**:

1. Renaming core directories or packages (`apps/web`, main backend package, etc.) without explicit instruction.
2. Modifying Husky, CI, or lint configurations unless the task explicitly calls for it.
3. Editing `artifacts/FuncTechSpec.md` or `CodingStandards.md` unless directed.
4. Introducing new major libraries or frameworks without justification and approval.
5. Leaving TODOs without clear context; prefer to either implement or open a clearly described placeholder with a comment.

---

## 9. Summary

- Follow the **FuncTechSpec** for behavior.
- Follow this document for **code style and structure**.
- Aim for code that looks like it was written by a careful, senior engineer: clean, modular, well-typed, and easy to understand.
