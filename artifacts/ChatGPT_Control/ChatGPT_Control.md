# ChatGPT Control Document – Media Promo Localizer

> **Purpose:** This document is the the persistent “external state” for ChatGPT when working on the **Media Promo Localizer** project.  
> It captures project context, invariants, conventions, and key decisions so that new ChatGPT threads can resume work reliably
> even after context limits are reached.

---

## 1. Document Metadata

- **Project:** Media Promo Localizer (Paramount-style promo image localization PoC)
- **Role of this doc:** External memory / control doc for ChatGPT only
  - Stored under: `artifacts/ChatGPT/ChatGPT_Control.md`
  - **Not** a Cursor control document (lives in subfolder on purpose)
- **Owner:** Chris Hennes (product owner / architect)
- **Primary AI collaborators:**
  - ChatGPT – architectural partner, spec/design author, dev-process designer
  - Cursor / Claude Sonnet – primary code generation + repo-aware assistant
- **Last major revision:** 2025-12-10
- **Revision summary:** Initial version of ChatGPT control doc created and aligned with new control-doc system.

---

## 2. Project Snapshot (for New Threads)

High‑level context to load into any new ChatGPT thread for this project.

### 2.1 Project Goal

Build a **Media Promo Localizer** PoC that:

- Accepts **movie/TV promotional artwork** (e.g., posters, one-sheets).
- Extracts text via OCR, translates/localizes it, and inpaints the localized text back into the image.
- Provides a simple **web UI** for uploading assets, inspecting OCR/translation, and downloading localized outputs.
- Is implemented as:
  - A **FastAPI backend** (current focus, Sprint 2 completed).
  - A **React/Vite/TypeScript frontend** (Sprint 1 previously completed).
- Is designed as a credible PoC for **studio clients (e.g., Paramount)** with clean architecture and production‑style practices.

### 2.2 Current Stage (as of this doc)

- **Sprint 2 – Backend mock pipeline** has been implemented:
  - FastAPI backend with health + jobs endpoints.
  - In‑memory/mock job store & mock pipeline (`mock_engine`) that simulates OCR/translation/inpainting.
  - Tests written with `pytest` + `pytest-asyncio`; **11 tests passing** at last run.
  - Backend runs successfully via Uvicorn and exposes `/health` and job endpoints.
- Control documents for the project have been **refactored & consolidated** and live in `/artifacts`:
  - `FuncTechSpec.md` – functional + technical specification (authoritative behavior description).
  - `DevPlan.md` – sprint roadmap & phase planning.
  - `DevProcess.md` – dev workflow, branching strategy, codegen strategy, quality gates.
  - `DevProgress.md` – chronological log of completed work.
  - `DevChecklist_Sprint2.md` – detailed backend sprint checklist (mostly complete).
  - `CodingStandards.md` – code style & conventions.
  - `CommitGuide.md` – Git/commit conventions.
  - `API_Definition.md` – consolidated API contract (endpoints, schemas, error models).
  - `API_Providers.md` – (if present) provider‑specific notes; otherwise folded into `API_Definition.md`.

When spinning up a new ChatGPT thread for this project, **Chris will typically upload** at least:

1. `artifacts/ChatGPT/ChatGPT_Control.md` (this file)
2. `artifacts/FuncTechSpec.md`
3. `artifacts/DevProcess.md`

ChatGPT will then request additional docs only as needed.

---

## 3. Invariants & Global Conventions (ChatGPT‑Side)

These are cross‑thread assumptions ChatGPT should always maintain unless the documents are explicitly changed.

### 3.1 Architectural Invariants

- **Backend:** FastAPI app under `apps/API/app`, following the API spec in `API_Definition.md`.
- **Frontend:** React/Vite/TypeScript web app under `apps/web` (already prototyped in Sprint 1).
- **Environment:** Chris’s dev box is a mid‑2015 MBP; avoid heavyweight dependencies that require exotic build chains or huge resource footprints.
- **Quality bar:** PoC but with **production‑style discipline**:
  - Clear layering and separation of concerns.
  - Tests for critical paths, especially API contracts and error handling.
  - Explicit handling of mock vs real providers in future sprints.

### 3.2 Process & Collaboration Invariants

- **Source of truth for behavior:** `FuncTechSpec.md` and `API_Definition.md`.
- **Source of truth for workflow:** `DevProcess.md` and `DevPlan.md`.
- **Source of truth for status:** `DevProgress.md` + sprint checklist (`DevChecklist_SprintN.md`).
- **Control docs must not conflict.** Any proposed change that contradicts an existing doc must:
  1. Be discussed explicitly.
  2. Be recorded as a revision to the relevant doc(s).
  3. Include a short entry in `DevProgress.md` and, if appropriate, this control doc.

- **Cursor is the primary codegen engine.**  
  ChatGPT’s responsibilities are:
  - Designing / updating specs and control docs.
  - Helping design Cursor prompts and checklists.
  - Troubleshooting, reasoning, and “explaining what’s going on” when things get weird.
  - Helping Chris debug local issues by reasoning from logs, screenshots, etc.

### 3.3 Versioning & Health‑check Conventions

- **Versioning:** Use `MAJOR.MINOR.PATCH+buildmetadata` when needed, but do **not** over‑optimize early.
  - Backend should expose its version via the `/health` endpoint and/or an `/about`-style route.
  - Frontend should display a small “About” dialog with:
    - UI version
    - Backend version (fetched from API)
- **Health Endpoint (`/health`):**
  - Must return `{"status": "ok", "uptimeSeconds": <number>, "version": "<backend-version>"}` at minimum.
  - Uptime derived from `app.state.startup_time` set in FastAPI lifespan.

---

## 4. How ChatGPT Should Work in a New Thread

This is the **standard operating procedure** when Chris spins up a new ChatGPT conversation for this project.

### 4.1 First Response Checklist

When you see the Quickstart Snippet and the uploaded docs:

1. **Confirm project & docs loaded.**
   - Summarize: project, current sprint, and key constraints in 3–6 bullets.
2. **Ask minimally for any additional files you truly need.**
   - Examples: `DevPlan.md` when planning a new sprint, `DevChecklist_Sprint2.md` when reviewing backend work.
3. **Restate your role for this thread**, e.g.:
   - “In this thread I’ll act as your senior architect + dev‑process partner, focusing on control docs, Cursor prompts, and troubleshooting.”

Avoid re‑asking questions whose answers are already in the uploaded docs unless something is unclear or contradictory.

### 4.2 Updating This Control Document

Whenever we make a **persistent decision** (not just a one‑off for a single prompt), ChatGPT should:

1. Say explicitly:
   > “This feels like a change that belongs in `ChatGPT_Control.md`. I propose updating section X with Y.”
2. After agreement (or lack of objection), regenerate **the entire file** with the new content integrated.
3. Provide a new download link so Chris can overwrite `artifacts/ChatGPT/ChatGPT_Control.md` and commit it.

Examples of things that belong here:

- New long‑term conventions (“Always use `pytest` + `pytest-asyncio` for backend tests”).
- Changes to how we structure Cursor prompts or sprints.
- Changes to how we coordinate between ChatGPT and Cursor.
- Any “this is how Chris likes to work” project‑specific patterns.

---

## 5. Coordination with Cursor

This section defines how ChatGPT should design prompts & artifacts for Cursor.

### 5.1 Cursor’s Control Docs (Quick Map)

These files in `/artifacts` are **intended for Cursor** and human devs:

- `FuncTechSpec.md` – “what the system must do”; main spec.
- `API_Definition.md` – exact endpoints, request/response bodies, error codes.
- `DevPlan.md` – sprints, milestones, high‑level roadmap.
- `DevProcess.md` – branching, CI/CD, codegen rules, test strategy.
- `DevChecklist_SprintN.md` – task‑level checklist for a given sprint.
- `DevProgress.md` – chronological progress log (Cursor + humans both append).
- `CodingStandards.md` – style and implementation rules.
- `CommitGuide.md` – Git conventions and commit message format.

### 5.2 Principles for Designing Cursor Prompts

When I (ChatGPT) am asked to craft a Cursor plan/prompt:

- **Scope clearly.** Each major coding effort should correspond to:
  - A sprint implementation prompt (`Implement Sprint N backend`, `Implement Sprint N UI`), or
  - A focused bugfix / refactor prompt.
- **Feed Cursor only the necessary docs.** At minimum for backend work:
  - `FuncTechSpec.md`
  - `API_Definition.md`
  - `DevProcess.md`
  - The relevant `DevChecklist_SprintN.md`
- **Include instructions for progress logging:**
  - Cursor should **append** status entries to `DevProgress.md` per logical unit of work.
  - Cursor should update the sprint checklist (or restated checklist) as tasks are completed.
- **On error or incomplete work:** prefer **prompting Cursor to fix its own code** via a targeted prompt, rather than us editing everything by hand.

### 5.3 “Ignore Subfolders Under /artifacts” Rule

For Cursor prompts, I should always remind:

> “Ignore everything under `/artifacts/**` subfolders unless explicitly instructed to read a specific file (e.g., historic prompts or ChatGPT docs). Only treat top‑level files in `/artifacts` as active control docs.”

This keeps historical junk and ChatGPT‑specific files from polluting Cursor’s behavior.

---

## 6. Running Log of Key Decisions

This is **intentionally concise**; detailed narrative belongs in `DevProgress.md`.

1. **2025‑12‑10 – Control doc refactor finalized**
   - All project control docs restructured; `API_Definition.md` consolidated.
   - `ControlDocsInfo.md` created to describe roles & responsibilities of each control doc.
   - `ChatGPT_Control.md` created under `artifacts/ChatGPT/` as ChatGPT’s external state.
2. **2025‑12‑10 – Cursor error‑fixing SOP**
   - When FastAPI/Uvicorn/tests break, we prefer to prompt Cursor to fix the issues in a new “fix the bug” plan prompt, rather than doing extensive manual edits.
3. **2025‑12‑10 – Health endpoint behavior**
   - `/health` must return status, uptimeSeconds, and version; uptime derived from `app.state.startup_time` set in FastAPI lifespan context.
4. **2025‑12‑10 – Context management approach**
   - Each new Cursor chat: load control docs from `/artifacts` and rely on them instead of long-lived conversations.
   - Each new ChatGPT thread: load `ChatGPT_Control.md`, `FuncTechSpec.md`, `DevProcess.md` at minimum.
5. **2025‑12‑10 – Frontend CI & Node / Rollup behavior**
   - Frontend GitHub Actions workflow must lint, type-check, and build the web app successfully on Node 20+.
   - Treat `react-refresh/only-export-components` as a **warning**, not an error, so files can export both components and shared constants.
   - If CI fails with Rollup optional native dependency errors, preferred fix is:
     1. Remove `node_modules` and the root `package-lock.json`.
     2. Run `npm install` at the repo root to regenerate the lockfile.
     3. Re-run `npm run -w @app/web lint` and `npm run -w @app/web build` locally, then commit the updated lockfile.

   - Each new Cursor chat: load control docs from `/artifacts` and rely on them instead of long-lived conversations.
   - Each new ChatGPT thread: load `ChatGPT_Control.md`, `FuncTechSpec.md`, `DevProcess.md` at minimum.

(As we move forward, we’ll append more items here when they are _truly_ cross‑thread decisions.)

---

## 7. Open Questions / Future Enhancements

Things that we know we will revisit later; they should not block current progress.

1. **API & UI version surface:**
   - We plan to expose version info in both `/health` and a UI “About” panel, but exact formatting and wiring may evolve.
2. **Long‑term storage via API:**
   - In the future, Chris may use the OpenAI API with tooling that automatically persists ChatGPT‑generated docs into Git.
   - When that happens, this doc’s “update” workflow will switch from “download link + manual commit” to an automated pipeline.

---

## Appendix A – Quickstart Snippet for New ChatGPT Threads

Chris can keep this snippet handy and paste it at the top of a new thread **after** uploading the three core docs:

> **Quickstart Snippet – Media Promo Localizer (ChatGPT Control)**
>
> I’m continuing work on the **Media Promo Localizer** project. I’ve uploaded three core control docs:
>
> 1. `artifacts/ChatGPT/ChatGPT_Control.md` – your external state for this project
> 2. `artifacts/FuncTechSpec.md` – functional + technical spec
> 3. `artifacts/DevProcess.md` – dev workflow, branching, and codegen process
>
> Please:
>
> - Read these docs and summarize the current project state, our role split between ChatGPT and Cursor, and where we left off.
> - Tell me which _additional_ control docs (if any) you want me to upload for this session (e.g., `DevPlan.md`, `DevProgress.md`, `DevChecklist_SprintN.md`, `CodingStandards.md`, `CommitGuide.md`).
> - Then ask me what I want to accomplish **today** and propose a short plan for this session.
>
> Going forward in this thread, whenever we make persistent decisions (new conventions, process changes, or cross‑thread rules), update `ChatGPT_Control.md`, regenerate the full file, and give me a new copy so I can commit it.

---

## Appendix B – How to Update This Document Safely

When revising `ChatGPT_Control.md`:

1. Maintain the overall section structure unless we explicitly agree to reorganize it.
2. Keep the **Running Log of Key Decisions** short and factual.
3. When adding new conventions, verify they do not conflict with:
   - `ControlDocsInfo.md`
   - `DevProcess.md`
   - `FuncTechSpec.md`
   - `API_Definition.md`
4. After generating a new version, clearly say something like:
   - “Here is the updated `ChatGPT_Control.md`; please overwrite the existing file under `artifacts/ChatGPT/` and commit it.”

This discipline lets us use ChatGPT effectively across many threads without losing context or introducing contradictory rules.
