# Media Promo Localizer – Control Documents Overview

> **Version History**
>
> - 2025‑12‑10 – v1.0 – Initial consolidated control‑doc overview for Cursor/Sonnet and human collaborators.

---

## 1. Purpose

This document is the **entry point** for anyone (human or AI) working on the Media Promo Localizer project.  
It explains:

- Which control documents exist in `/artifacts`
- What each one is responsible for
- How to use them together when designing, coding, or reviewing work
- How to safely handle **requirement changes** mid‑project
- How to keep context small while preserving project memory

Unless a prompt says otherwise, **Cursor/Sonnet and ChatGPT must treat the documents listed here as the only authoritative project‑level control docs.** Any other files in `/artifacts` or its subfolders are historical or scratch and must be ignored unless explicitly referenced.

---

## 2. Control Documents in `/artifacts`

All control docs live directly in the `/artifacts` directory (no subfolders):

1. **FuncTechSpec.md** – Functional & technical specification
   - Defines the product vision, user flows, system architecture, and non‑API behavior.
   - Canonical source of truth for _what the system should do_ and _why_.
   - If requirements change, they must be reflected here (see §4).

2. **API_Definition.md** – API contract (backend surface)
   - Canonical description of all public HTTP endpoints the backend exposes.
   - Includes request/response schemas, error models, and health/status behavior.
   - Frontend and backend must both treat this spec as authoritative.
   - **All provider‑specific behavior referenced by the API must be consistent with this spec.**

3. **DevPlan.md** – Project plan and milestones
   - High‑level roadmap of phases/sprints and objectives.
   - Captures _what we are doing next_ at the project level.
   - Only updated when planning or re‑planning; not during everyday coding.

4. **DevProcess.md** – Working agreements & workflow
   - Defines how we use branches, sprints, code review, CI, and tools.
   - Explains how Cursor/Sonnet and ChatGPT should behave as members of the dev team.
   - Describes how to move work from **idea → spec → implementation → review → release**.

5. **DevChecklist_SprintN.md** – Sprint‑specific implementation checklist(s)
   - One checklist per sprint, e.g. `DevChecklist_Sprint2.md`.
   - Detailed, actionable tasks that Cursor or a human dev can execute in order.
   - Acts as the **execution script** for codegen: tasks should be checked off as they are completed, not in bulk at the end.

6. **DevProgress.md** – Append‑only activity log
   - Chronological record of what was done, when, and by whom (human or AI).
   - Each entry represents a **logical unit of work** (e.g. “Implement Sprint 2 backend tests and fix health endpoint startup issues”).
   - Must be updated immediately after a unit of work completes and before starting the next one.

7. **CodingStandards.md** – Code and project conventions
   - Language‑specific and repo‑wide standards (Python, TypeScript/React, tests, logging, error handling, etc.).
   - Rules for how code should look and behave so that multiple contributors (human & AI) can work cleanly in the same repo.
   - Includes expectations for how AI tools interact with control docs and DevProgress/DevChecklist.

8. **CommitGuide.md** – Git usage & release conventions
   - Branch naming, commit message style (Conventional Commits), and tag/version schemes.
   - Specifies when to commit, how to write messages, and how to handle bug‑fix branches.
   - Defines how we surface versions and builds (e.g. via `/health` and UI “About” panels).

9. **API_Providers.md** – Provider notes (deprecated as a control doc)
   - Kept only as a light reference for external AI providers and capabilities.
   - **Not an authoritative contract.** The API surface must always match `API_Definition.md`.
   - Cursor/Sonnet should treat this file as informational only, never as a source of required behavior.

---

## 3. How Humans & AI Should Use These Docs

### 3.1 For Cursor/Sonnet (local repo agents)

When implementing or modifying code, Cursor/Sonnet should:

1. **Load control docs explicitly** at the start of a session:
   - Always read: `ControlDocsInfo.md`, `FuncTechSpec.md`, `API_Definition.md`, `DevProcess.md`, `CodingStandards.md`, and the current sprint’s `DevChecklist_SprintN.md`.
   - Optionally skim `DevPlan.md` for context on where we are in the roadmap.
2. **Scope context tightly**:
   - Only open additional files (including older prompts, archived context, or `/artifacts` subfolders) when the prompt explicitly instructs it to.
   - Treat subfolders under `/artifacts` as **ignored** by default (historical only).
3. **Follow the checklist**:
   - Use the active `DevChecklist_SprintN.md` as the step‑by‑step guide for work.
   - Before starting a task, re‑read the relevant checklist item.
   - After completing a task and verifying tests for that unit of work, mark the item as done in the checklist.
4. **Log progress**:
   - After each logical unit of work, append an entry to `DevProgress.md` describing:
     - What was done
     - Which checklist items were addressed
     - Which files were changed
     - How tests were run and their outcome

### 3.2 For ChatGPT (this assistant)

When helping design or guide changes, ChatGPT should:

1. Use these docs as the **stable memory** that survives context resets and new threads.
2. Prefer updating these docs (or suggesting updates) over relying on its own transient context.
3. When we need to start a “fresh” thread, generate/update a **context bundle** summarizing the current state, with links back to the relevant control docs.

### 3.3 For Human Collaborators

Humans should:

- Treat `/artifacts` as the **single source of truth** for project governance.
- Update control docs in small, clear diffs and commit them under `docs:` or `chore:` as appropriate.
- Never make large behavioral changes to the system without reflecting them in `FuncTechSpec.md` and/or `API_Definition.md`.

---

## 4. Handling Requirement Changes Safely

Requirements will change. The goal is to **capture those changes cleanly** without letting docs drift or contradict each other.

Whenever product behavior, API shape, or architecture needs to change:

1. **Update the spec first**
   - Edit `FuncTechSpec.md` to describe the new behavior.
   - If the API changes, update `API_Definition.md` as well.
   - Keep the description concise but unambiguous.

2. **Tag the change in Version History**
   - Add a new bullet to the `Version History` section at the top of the affected doc(s).
   - Reference the Git branch or issue ID if applicable (e.g. `feat/sprint3-job-cancellation`).

3. **Align plan & process**
   - If the change affects roadmap or scope, update `DevPlan.md`.
   - Add or adjust checklist items in the next `DevChecklist_SprintN.md`.
   - Note the change in `DevProgress.md` the first time work is done under the new requirement.

4. **Only then implement code**
   - Cursor/Sonnet and humans implement the change by following the updated checklist.
   - Tests must be adapted or extended to cover the new behavior.

This sequence ensures that **spec → plan → checklist → code** stay synchronized.

---

## 5. Versioning & “About” / Health Behavior

### 5.1 Semantic Version + Build ID

We use a simple, explicit versioning scheme:

- **Semantic Version**: `MAJOR.MINOR.PATCH` (e.g. `0.2.0`)
- **Build ID**: `YYYYMMDD.HHMM` or similar timestamp, generated at build time
- **Environment**: `local`, `qa`, `staging`, `prod`, etc.

The backend should expose these via the `/health` endpoint (see `API_Definition.md`), for example:

```json
{
  "status": "ok",
  "uptimeSeconds": 123,
  "version": "0.2.0",
  "buildId": "20251210.1345",
  "environment": "local"
}
```

For UI‑based apps, the frontend should also display this information in an **“About” dialog** or panel, so support can easily confirm what build a user is running.

### 5.2 Tagging & Releases

`CommitGuide.md` defines how we:

- Name branches for features, bugs, and sprints
- Use **Conventional Commits** for messages
- Apply Git tags to represent releases (e.g. `v0.2.0-sprint2-backend`)

All of these should align with the version and build metadata surfaced by the app.

---

## 6. Subfolders Under `/artifacts`

Subfolders (e.g. `/artifacts/archive`, `/artifacts/prompts`, `/artifacts/context`) are allowed, but:

- They are **not** control docs.
- They exist only for history, scratch, or reference.
- Cursor/Sonnet and ChatGPT must ignore them **unless** a prompt explicitly instructs them to open a specific file there.

This rule keeps context clean and prevents old prompts or obsolete ideas from silently influencing code generation.

---

## 7. When Context Runs Out

When a ChatGPT or Cursor session gets long or starts to feel sluggish:

1. **Finish the current logical unit of work** and log it in `DevProgress.md`.
2. If needed, create or update a short **context bundle** file in `/artifacts` (or a subfolder) summarizing:
   - Current architecture
   - Current sprint state and remaining checklist items
   - Any open questions or TODOs
3. Start a new session, load the control docs and the latest context bundle, and continue from there.

By relying on these control docs as persistent memory, we can treat each new session as **stateless** while still carrying the full project history forward in a controlled, explicit way.
