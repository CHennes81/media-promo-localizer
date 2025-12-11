# Media Promo Localizer – API Providers (Informational Only)

> **Version History**
>
> - 2025‑12‑10 – v1.1 – Marked this file as informational only and clarified that `API_Definition.md` is the canonical contract.
> - 2025‑11‑xx – v1.0 – Initial notes on potential provider integrations.

---

## 1. Purpose

This file is **not** a control document for the Media Promo Localizer API surface.

It exists only to:

- Capture high‑level notes about potential or actual external providers (OCR, translation, inpainting, storage, etc.).
- Describe provider capabilities, trade‑offs, and configuration at a conceptual level.
- Provide background for future design decisions about swapping or extending providers.

The **authoritative API contract** for all client‑visible HTTP endpoints is defined in:

- `API_Definition.md` – canonical request/response schemas and error models.

If anything in this file conflicts with `API_Definition.md`, **`API_Definition.md` wins.**

---

## 2. Provider Notes (High Level)

When documenting providers here, focus on:

- Provider name and role (e.g. “Google Vision – OCR”, “Claude / GPT – translation/localization”, “Stable Diffusion – inpainting”).
- Key strengths and weaknesses relevant to our use case.
- Any constraints that might affect the API design (rate limits, latency, file size limits, supported languages, etc.).
- Operational concerns: quotas, cost, authentication model, regions.

Example structure for a provider entry:

```markdown
### Google Vision (OCR)

- **Role**: Extract text from poster images.
- **Strengths**: High accuracy on Latin scripts, robust layout detection.
- **Weaknesses**: Cost at scale, latency on large images.
- **Constraints**:
  - Max image size: …
  - Rate limits: …
- **Notes**:
  - Text extraction results must be normalized into our internal schema before passing to translators.
```

Again: treat these as **design notes**, not as requirements. Requirements live in `FuncTechSpec.md` and `API_Definition.md`.

---

## 3. Usage Guidelines for AI Tools

Cursor/Sonnet and ChatGPT should:

- Ignore this file when determining what endpoints or request/response bodies should look like.
- Only consult it when the task is explicitly about provider selection, capabilities, or trade‑offs.
- Never auto‑generate code that assumes a specific provider purely because of notes written here; use the abstract contracts from `API_Definition.md` and `FuncTechSpec.md` instead.
