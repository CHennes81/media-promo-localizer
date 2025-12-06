# External Provider API Reference

This document captures the **minimal, implementation-focused details** for calling external providers
used by the Media Promo Localizer backend. It is intentionally separate from the main API contract
(`API_Documentation.md`) so that vendor integrations can be swapped or updated without changing the
public API.

> **IMPORTANT:** This file is an internal implementation guide. The public API exposed to the
> frontend MUST always conform to `API_Documentation.md`, regardless of which providers are used
> under the hood.

---

## 1. Overview

The backend may call the following external services in **live** mode:

1. **OCR Provider** – Google Cloud Vision
2. **Localization / Translation Provider** – Claude
3. **Inpainting / Image Editing Provider** – Replicate (SDXL Inpainting)

Each section below should include:

- Endpoint URL (or client library config)
- Required headers (including how to pass API keys via environment variables)
- Minimal request JSON/body template
- Example response shape (trimmed to only the fields we actually use)
- Notes on rate limits, size limits, and common error cases

Do **not** paste full provider documentation here – only the small, curated snippets that our backend
actually depends on.

---

## 2. Google Cloud Vision (OCR)

This section should document how we call Vision for **text detection** on poster images.

Suggested subsections:

- 2.1 **Endpoint & Authentication**
  - Base URL
  - Auth mechanism (API key, service account, etc.)
  - Relevant environment variables (for example `GCP_PROJECT_ID`, `GCP_CREDENTIALS_JSON`, or `GOOGLE_APPLICATION_CREDENTIALS`)

- 2.2 **Text Detection Request Template**
  - Example JSON body for text detection (or client library call shape)
  - Any image size/format constraints we care about

- 2.3 **Response Shape (Trimmed)**
  - Only the pieces we actually use:
    - Detected text
    - Bounding boxes / polygon coordinates
  - Notes on how we map this to `detectedText` in our own API.

- 2.4 **Limits & Error Notes**
  - Max image size / dimensions we care about
  - Common error types and recommended handling.

---

## 3. Claude (Localization / Translation)

This section should document how we call Claude to turn **English marketing text** (titles, taglines,
etc.) into localized, cinematic text in the target language.

Suggested subsections:

- 3.1 **Endpoint & Authentication**
  - Base URL and model name(s) used (for example Sonnet)
  - Required headers and auth
  - Relevant environment variables (for example `CLAUDE_API_KEY`)

- 3.2 **Prompt / Request Template**
  - Example request body that:
    - Provides source text.
    - Specifies target language / locale (for example `es-MX`, `fr-FR`, `ja-JP`).
    - Instructs Claude to produce _cinematic, marketing-style_ localized text rather than a literal translation.

- 3.3 **Response Shape (Trimmed)**
  - How we extract the final localized string(s) from the response.
  - Any safety/guardrail handling we care about.

- 3.4 **Style & Tone Guidelines**
  - Short notes describing the intended tone (for example “bold, cinematic, trailer tagline style”).
  - Any constraints (for example “keep under X characters where possible”).

---

## 4. Replicate (SDXL Inpainting)

This section should document how we call Replicate to perform **inpainting** and render localized text
back into the poster image.

Suggested subsections:

- 4.1 **Endpoint & Authentication**
  - Base URL and model identifier (for example a specific SDXL inpaint model).
  - Required headers and auth.
  - Relevant environment variables (for example `REPLICATE_API_TOKEN`).

- 4.2 **Inpaint Request Template**
  - Expected image inputs (original image and optional preprocessed/masked version).
  - Mask format (how we pass the inpaint mask derived from OCR bounding boxes).
  - Prompt template:
    - How we pass the localized text.
    - Style guidance (for example “cinematic poster title, matching original style as closely as possible”).

- 4.3 **Response Shape (Trimmed)**
  - How we obtain the final output image URL or binary.
  - Any post-processing steps (for example copying to our own storage, generating a thumbnail).

- 4.4 **Limits & Performance Notes**
  - Recommended image resolution for best results.
  - Timeout expectations, typical latency.
  - Error handling guidance.

---

## 5. Configuration & Environment Variables

This section should list **all environment variables** required for live mode, for example:

- `LOCALIZATION_MODE` – `mock` or `live`
- `GCP_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS` or equivalent
- `CLAUDE_API_KEY`
- `REPLICATE_API_TOKEN`

For each variable, briefly describe:

- What it is used for.
- Whether it is required for local development, production, or both.
- Any security notes (for example “never commit this value to git; configure in Railway dashboard”).

---

Once you paste the minimal examples from each provider's docs into this skeleton, Cursor/Sonnet can
use this file as the single source of truth for **how to call external services**, while
`API_Documentation.md` remains the stable public contract for the frontend.
