# Media Promo Localizer – API Contract (Async Job Model)

Version: 0.1  
Status: Draft (MVP PoC)

## 1. Overview

The Media Promo Localizer backend exposes an **asynchronous job-based API** for localizing film/TV key art (poster images).

Key principles:

- **Async-first**: Clients create a job and poll for completion.
- **Vendor-neutral**: The API surface is independent of the underlying OCR / translation / inpainting providers.
- **Stable contracts**: Frontend and backend development proceed independently against this spec.
- **MVP-friendly**: Single-image jobs initially, extensible to batches later.

All endpoints are versioned under:

- Base URL (example): `https://api.media-promo-localizer.com`
- Version prefix: `/v1`

> **Note:** For PoC/demo environments, the base URL may be a Railway or similar URL, but the path and payloads MUST follow this contract.

---

## 2. Endpoint Summary

### 2.1 Create Localization Job

**POST** `/v1/localization-jobs`

Creates a new localization job for a single poster image.

- **Auth**: None for MVP (demo only).
- **Content-Type**: `multipart/form-data`

#### Request Fields

- `file` (required)
  - Type: `file` (binary)
  - Description: Poster image to localize.
  - Supported formats: `image/jpeg`, `image/png` (more can be added later).

- `targetLanguage` (required)
  - Type: `string`
  - Description: BCP 47 language tag (e.g. `es-MX`, `fr-FR`, `pt-BR`, `ja-JP`).

- `sourceLanguage` (optional)
  - Type: `string`
  - Description: BCP 47 language tag of source text. If omitted, system attempts auto-detection.

- `jobMetadata` (optional)
  - Type: `string` (JSON-encoded object)
  - Description: Optional metadata for client tracking (e.g. user ID, campaign, asset ID). Opaque to the backend.

#### Example Request (conceptual)

```http
POST /v1/localization-jobs HTTP/1.1
Content-Type: multipart/form-data; boundary=---XYZ

---XYZ
Content-Disposition: form-data; name="targetLanguage"

es-MX
---XYZ
Content-Disposition: form-data; name="file"; filename="poster.jpg"
Content-Type: image/jpeg

<binary JPEG>
---XYZ--
```

#### Response – 202 Accepted

```json
{
  "jobId": "loc_01HWQJ9M0F6S4E83X9X2ZF7T3G",
  "status": "queued",
  "createdAt": "2025-12-04T19:01:23.456Z",
  "estimatedSeconds": 8
}
```

Fields:

- `jobId` (string, required): Unique job identifier.
- `status` (string, required): Initial status. One of:
  - `queued`
  - `processing`
- `createdAt` (ISO 8601 string): Server-side creation timestamp.
- `estimatedSeconds` (number, optional): Rough guess for UX only. May be `null` or omitted.

#### Error Responses

- **400 Bad Request**
  - Missing file or targetLanguage, unsupported language format, invalid metadata JSON.
- **415 Unsupported Media Type**
  - File is not a supported image type.
- **500 Internal Server Error**
  - Unexpected backend failure.

---

### 2.2 Get Localization Job Status / Result

**GET** `/v1/localization-jobs/{jobId}`

Returns the current status of a localization job, and the result when complete.

- **Auth**: None for MVP.
- **Content-Type**: `application/json`

#### Path Parameters

- `jobId` (required): ID returned from the create endpoint.

#### Response – 200 OK (General Shape)

```json
{
  "jobId": "loc_01HWQJ9M0F6S4E83X9X2ZF7T3G",
  "status": "processing",
  "createdAt": "2025-12-04T19:01:23.456Z",
  "updatedAt": "2025-12-04T19:01:30.789Z",
  "progress": {
    "stage": "inpaint",
    "percent": 68,
    "stageTimingsMs": {
      "ocr": 1200,
      "translation": 800,
      "inpaint": 4300,
      "packaging": 0
    }
  },
  "result": null,
  "error": null
}
```

#### Status Values

- `queued` – Job accepted but not yet started.
- `processing` – Job actively running (any stage).
- `succeeded` – Job finished successfully; `result` is populated.
- `failed` – Job failed; `error` is populated and `result` is `null`.
- `canceled` – Reserved for future use (not used in MVP).

#### Progress Object

Optional but recommended for UX:

```json
"progress": {
  "stage": "ocr",
  "percent": 42,
  "stageTimingsMs": {
    "ocr": 1200,
    "translation": 800,
    "inpaint": 0,
    "packaging": 0
  }
}
```

Fields:

- `stage`:
  - `ocr`
  - `translation`
  - `inpaint`
  - `packaging` (final assembly/output preparation)
- `percent`: Rough overall completion percentage (0–100).
- `stageTimingsMs`: Per-stage elapsed time in milliseconds (may be partial while running).

For early MVP, `progress` may be coarse-grained (e.g. bump from 10 → 50 → 90 → 100).

---

### 2.3 Successful Result Shape (`status = "succeeded"`)

When `status` is `succeeded`, the `result` field is populated:

```json
"result": {
  "imageUrl": "https://cdn.media-promo-localizer.com/jobs/loc_01HWQJ9M0F6S4E83X9X2ZF7T3G/output.png",
  "thumbnailUrl": "https://cdn.media-promo-localizer.com/jobs/loc_01HWQJ9M0F6S4E83X9X2ZF7T3G/thumb.png",
  "processingTimeMs": {
    "ocr": 1200,
    "translation": 800,
    "inpaint": 4300,
    "total": 6800
  },
  "language": "es-MX",
  "sourceLanguage": "en-US",
  "detectedText": [
    {
      "text": "THE GREAT HEIST",
      "boundingBox": [100, 200, 800, 280],
      "role": "title"
    },
    {
      "text": "COMING SOON",
      "boundingBox": [120, 900, 780, 950],
      "role": "tagline"
    }
  ]
}
```

Fields:

- `imageUrl` (string, required): Publicly accessible URL to the localized poster image.
- `thumbnailUrl` (string, optional): Smaller preview version for UI.
- `processingTimeMs` (object, required):
  - `ocr`, `translation`, `inpaint`, `total` (numbers, ms).
- `language` (string, required): Final target language code.
- `sourceLanguage` (string, optional): Detected/assumed source language.
- `detectedText` (array, optional):
  - Per-text-element info (optional for MVP, but valuable later).
  - Each entry:
    - `text` (string): The original or translated text segment.
    - `boundingBox` (array of 4 numbers): `[x1, y1, x2, y2]` in pixel coordinates relative to original image.
    - `role` (string): Soft classification (e.g. `title`, `tagline`, `credits`, `rating`, `other`).

For **MVP**, `detectedText` may be stubbed or simplified, but the shape should be respected so the frontend and analytics can rely on it later.

---

### 2.4 Failed Result Shape (`status = "failed"`)

When `status` is `failed`, `error` is populated and `result` is `null`:

```json
"error": {
  "code": "INPAINT_MODEL_TIMEOUT",
  "message": "Inpainting backend did not respond within 30 seconds.",
  "retryable": true
}
```

Standard error codes to start with:

- `INVALID_INPUT`
- `UNSUPPORTED_MEDIA_TYPE`
- `NOT_FOUND`
- `INTERNAL_ERROR`
- `OCR_MODEL_ERROR`
- `TRANSLATION_MODEL_ERROR`
- `INPAINT_MODEL_ERROR`
- `OCR_MODEL_TIMEOUT`
- `TRANSLATION_MODEL_TIMEOUT`
- `INPAINT_MODEL_TIMEOUT`

Fields:

- `code` (string, required): Machine-readable error code.
- `message` (string, required): Human-readable explanation.
- `retryable` (boolean, required): Indicates whether a re-submit might succeed.

#### Error HTTP Statuses

- **404 Not Found** – Unknown `jobId`.
- **500 Internal Server Error** – Unhandled exceptions.

---

## 3. Polling Recommendations (Frontend)

The frontend should:

1. Call `POST /v1/localization-jobs` with the uploaded file + target language.
2. Receive `jobId` and immediately:
   - Navigate to a “Processing” view for that job.
   - Start polling `GET /v1/localization-jobs/{jobId}`.

### Suggested Polling Strategy

- Poll interval: **1–2 seconds** for demo (can be tuned later).
- Timeout: e.g. **60 seconds** before giving up and showing a failure message.
- Stop polling when `status` is:
  - `succeeded` → show result.
  - `failed` → show error.
  - `canceled` → stop (future behavior).

For MVP, simple polling is sufficient; webhooks or SSE can be considered later.

---

## 4. HTTP Status Codes Summary

- **202 Accepted** – Job created successfully.
- **200 OK** – Job status/result retrieved successfully.
- **400 Bad Request** – Invalid parameters, missing file, invalid metadata JSON.
- **404 Not Found** – Unknown `jobId`.
- **415 Unsupported Media Type** – File is not a supported image format.
- **500 Internal Server Error** – Unexpected backend failure.

---

## 5. Vendor Abstraction (Internal Notes)

This contract is **vendor-agnostic**:

- OCR may be Google Vision, Azure, or an open-source OCR model.
- Translation may be Claude, Google Translate, or another LLM.
- Inpainting may be SDXL, Llama Inpainting, etc.

The backend implementation MUST transform vendor-specific responses into the unified `result` shape defined above.

Frontends and executives **must never see vendor-specific codes or payloads**.

---

## 6. Future Extensions (Out of Scope for MVP, Reserved)

These are NOT required for the MVP but reserved for future versions:

- **Batch jobs**
  - `POST /v1/localization-batches`
  - Multi-image jobs with aggregated status.

- **Webhook callbacks**
  - Client-specified URL to notify when job completes.

- **Authentication / API keys**
  - Required for production environments.

- **Rich asset bundles**
  - Multiple output renditions, layered PSD export, etc.

## 7. Implementation Modes (Mock vs Live)

The API contract above is fixed and MUST be respected by all implementations.

For development and demo purposes, there will be at least two internal pipeline implementations behind this API:

- **Mock (Dummy) Implementation**
  - Used in early sprints and for fast, low-cost UI polishing.
  - Does NOT call external providers.
  - Simulates the OCR → translation → inpaint stages, including:
    - Plausible `progress.stage` transitions.
    - Plausible `stageTimingsMs`.
  - Returns either:
    - A fixed sample output image, or
    - A locally generated placeholder image.
  - Selected via configuration (for example `LOCALIZATION_MODE=mock`).

- **Live Implementation**
  - Calls real external AI services (such as Google Vision, Claude, Replicate).
  - Produces an actual localized poster image from the uploaded asset.
  - Populates real timing data and (optionally) `detectedText`.
  - Selected via configuration (for example `LOCALIZATION_MODE=live`).

Both implementations MUST:

- Expose the same endpoints and payloads defined in this document.
- Never leak vendor-specific payloads or error formats to callers.
