AI Context Bundle — Media Promo Localizer

Version 1.0 — December 2025
Purpose: This document preserves all critical knowledge required to continue development with Claude.

📌 PROJECT OVERVIEW

Project Name: Media Promo Localizer (Internal name only; final branding TBD)
Goal: Automate localization of film/TV poster key art by:

Translating original text into a target language.

Performing seamless inpainting / style-matching placement.

Outputting studio-ready localized versions.

Core Deliverable: A production-style demo web app for studio executives.
Must demonstrate: Speed, automation, quality, scalability potential.

⚙️ ARCHITECTURE SUMMARY
Frontend

React + Vite + TypeScript

UI Requirements:

Login screen (dummy auth: accept any credentials)

Upload poster image

Select target languages

Show preview + comparison slider (original vs localized)

Download options (PNG, possibly layered asset later)

Animated processing state (not just text)

Backend

Python FastAPI

Runs on Railway for low-cost hosting.

Exposes image localization endpoint:

POST /localize

Must return:

{
"imageUrl": "...",
"processingTimeMs": {
"ocr": 123,
"translation": 456,
"inpaint": 789,
"total": 1368
},
"language": "es-MX"
}

ML / Services
Component Tool
OCR Google Vision / Tesseract fallback
Translation Claude/Google (final choice TBD per pricing/quality)
Inpainting HuggingFace Llama Inpaint; fallback Stable Diffusion if needed
UI Hosting Cloudflare Pages
Backend Hosting Railway
Asset Storage Cloudflare R2 (optional for v1; can serve base64 response initially)
Reliability Notes

Cloudflare, Google, Railway, and HuggingFace are sufficiently trusted for MVP.

Llama/SD inpainting models are stable and widely used.

Cost optimization handled after MVP sprint.

📂 REPO STRUCTURE & BRANCHING
Branches
Branch Purpose
dev Claude writes here only
qa Human-reviewed integration + CI tests
main Production demo branch
Branch Merging Rules

Claude ONLY commits to dev

Humans review code → merge to qa

CI runs → if passes → manual merge to main

📥 CI/CD REQUIREMENTS
Auto on PR to dev or qa:

pnpm install

pnpm lint (when introduced)

pnpm type-check

pnpm build

Python side: pytest if tests exist, else flake8 + import check

Auto Deploy

merge to main → triggers:

Frontend → Cloudflare Pages deployment

Backend → Railway deployment

🧠 CLAUDE DEVELOPMENT PROTOCOL

Claude must always:

Read artifacts/ before doing any task

Update artifacts/DevProgress.md after each sprint

NEVER modify code + tests simultaneously

Must obey flag: either CODE_MODE or TEST_MODE

Work only on the dev branch

Submit commits as atomic units (one feature or sprint objective only)

📑 ARTIFACTS IN USE
File Purpose
FuncTechSpec.md Full system specification
CodingStandards.md Rules: formatting, naming, error handling, organization
DevProcess.md High-level AI interaction guidelines
DevPlan.md Sprint layout + objectives
DevProgress.md Claude must update this every sprint
AI_ContextBundle.md ✔ This document — the master context
🧪 SPRINT STRATEGY
Sprint 1: Frontend Scaffolding

Auth screen (dummy login)

Upload UI

Language selector

Temporary stubbed "localize()" API returning fake data

Animated processing indicator

Sprint 2: Backend Scaffolding

FastAPI + dummy /localize

Accepts file + language

Returns JSON with fake timings + base64 placeholder

Sprint 3+: Integrations

Real OCR → then translation → then inpainting

🔐 KEYS & SECURITY

DO NOT hardcode keys in repo.

Use .env.\* files and CI secret injection.

Claude must never write plaintext keys.

📌 GUIDELINES FOR PROMPTING CLAUDE

When starting a coding session, always supply:

“Read and follow all files in artifacts/.
Follow FuncTechSpec.md + CodingStandards.md + DevProcess.md.
Update DevProgress.md after completing sprint objectives.
Commit only to dev branch.
Switch between CODE_MODE or TEST_MODE as required.
Implement Sprint X only.”

NEVER ask Claude to “fix failing tests” and “modify code” in the same message.

🔄 FAIL-SAFE RECOVERY

If Claude begins generating confusing or overlapping outputs:

Reset context.

Provide ONLY the artifacts/ package.

Specify exact Sprint objective again.

If code becomes broken:

Revert dev branch to last stable QA commit.

Restart sprint objective ONLY.

🎯 MVP SUCCESS CRITERIA

Executives can upload a poster → select a language → receive a credible, localized version.

UI is clean and impressive (animations during processing).

Output is visually believable for real workflows.

Performance timings are displayed for shock value.

📌 FINAL REMINDER

Claude is a senior engineer, not a junior prompt monkey.
Give it constraints + specs + goals, then let it build autonomously.

✔ Context Bundle Complete

This document is sufficient to re-initiate development anywhere.
