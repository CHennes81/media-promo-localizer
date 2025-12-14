# Cursor Spec: Credits Block Detection & Semantic Grouping (Appendix A)

**Project:** Media Promo Localizer (Poster Localization PoC)  
**Scope:** Implement _Credits Block Detection_ + _Credits Semantic Grouping_ as described in ChatGPT_Control Appendix A and FuncTechSpec credits-band two-pass model. fileciteturn0file0 fileciteturn0file1  
**Style/Rules:** Follow repository CodingStandards and ControlDocsInfo governance. fileciteturn0file3 fileciteturn0file5  
**API Safety:** Do not introduce breaking API changes; keep outputs backwards compatible with existing LineRegions/DetectedText contract. fileciteturn0file2

---

## 0. Outcome

After this change, the backend pipeline can:

1. **Detect whether a credits block exists**
2. **Locate it** (including rotation)
3. **Preserve “small discrete” overlay elements** (logos/badges/URLs/social) with their **original geometry**
4. **Extract a high-resolution sub-image** for the detected credits block (from the original full-res upload)
5. Run a specialized **credits OCR + grouping pass** producing structured **CreditGroups** (names vs titles vs credentials)
6. Emit **high-signal logs** that prove the detection and grouping worked end-to-end.

Non-goals (explicitly out of scope for this task):

- Rendering/inpainting changes
- UI changes
- DAM/PSD integration
- Any “final” translation policies beyond marking what is localizable vs locked

---

## 1. Integration Constraints / Guardrails

### 1.1 Do NOT regress existing OCR stability

- Keep the current rotation-aware OCR line reconstruction behavior.
- Credits detection must be _additive_ (new outputs + logs), not disruptive.

### 1.2 Preserve discrete overlay elements (Pass 1)

Pass 1 does **not** delete anything. It:

- identifies overlay candidates
- records their geometry and text (if any)
- marks them as locked/ignored-for-translation
- excludes them only from the _credits-block dense text_ clustering step

These overlays are critical future assets for exact replacement.

### 1.3 Use credits vocabulary as a scoring boost (not a hard gate)

Credits blocks contain many common role phrases (“Directed by”, “Executive Producers”, etc.).  
Use this as a **confidence boost** in Pass 2 scoring and as a **classification hint** in grouping.  
Never require it for detection (OCR can be noisy).

---

## 2. New Domain Data Model (Pydantic + Internal Types)

> Put models under a clear backend module (e.g., `apps/api/app/models/credits.py`) following existing patterns and CodingStandards. fileciteturn0file3

### 2.1 Geometry primitives (reuse existing where possible)

Assume existing `quad_norm`, `center_norm`, and `angle_deg` are available for LineRegions.  
If you already have a `Geometry` model, reuse it; otherwise define:

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class PointNorm(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)

class QuadNorm(BaseModel):
    # TL, TR, BR, BL (normalized coordinates)
    vertices: List[PointNorm] = Field(min_length=4, max_length=4)

class RegionGeometry(BaseModel):
    quad_norm: QuadNorm
    center_norm: PointNorm
    angle_deg: float
    # Optional derived axis-aligned bbox for convenience
    bbox_norm: Optional[List[float]] = None  # [x1,y1,x2,y2]
```

### 2.2 Credits band result container

```python
CreditsOverlayType = Literal["LOGO", "RATING_BADGE", "URL", "SOCIAL_HANDLE", "UNKNOWN"]

class CreditsOverlayElement(BaseModel):
    element_type: CreditsOverlayType
    text: Optional[str] = None
    geometry: RegionGeometry
    locked: bool = True  # always true

CreditGroupType = Literal["TITLE", "PROPER_NAME", "CERTIFICATION", "LOGO_IGNORED", "UNKNOWN"]

class CreditLine(BaseModel):
    text: str
    geometry: RegionGeometry
    font_height_norm: float  # proxy from quad height
    hints: List[str] = Field(default_factory=list)  # e.g. matched anchors

class CreditGroup(BaseModel):
    group_type: CreditGroupType
    lines: List[CreditLine]
    geometry: RegionGeometry  # union or representative (see §5.3)
    localizable: bool  # True for TITLE, False otherwise
    confidence: float = Field(ge=0.0, le=1.0)

class CreditsBlock(BaseModel):
    geometry: RegionGeometry  # oriented quad covering the whole credits block
    dominant_angle_deg: float
    source_line_region_ids: List[str] = Field(default_factory=list)  # stable IDs if available
    credit_groups: List[CreditGroup] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

class CreditsBandDetection(BaseModel):
    band_name: Literal["BOTTOM_BAND", "TOP_LITE_BAND"]
    band_bbox_norm: List[float]  # [x1,y1,x2,y2] normalized
    overlays: List[CreditsOverlayElement] = Field(default_factory=list)
    credits_block: Optional[CreditsBlock] = None
    confidence: float = Field(ge=0.0, le=1.0)
    debug: dict = Field(default_factory=dict)  # cluster scores, counts, etc.
```

### 2.3 Where to attach this in pipeline context

Add a new optional field in your pipeline context / job result object:

- `credits_detection: Optional[CreditsBandDetection]`

Do not remove or rename existing fields; keep backwards compatibility.

---

## 3. Config Constants (put in config module or a dedicated `credits_config.py`)

Use environment variables only if there is already precedent; otherwise start with constants.

Recommended normalized defaults:

```python
BOTTOM_BAND_Y_MIN = 0.70
BOTTOM_BAND_Y_MAX = 1.00

TOP_LITE_BAND_Y_MIN = 0.00
TOP_LITE_BAND_Y_MAX = 0.25

# Overlay heuristics
OVERLAY_AREA_SMALL = 0.0020        # tune
OVERLAY_HEIGHT_TINY = 0.030        # tune
OVERLAY_ASPECT_WIDE = 3.5          # tune

# Cluster / credits heuristics
CREDITS_LINE_COUNT_MIN = 8         # tune
CREDITS_FONT_HEIGHT_MAX = 0.030    # tune (small text)
CREDITS_ANGLE_STD_MAX = 8.0        # degrees

# Grouping / over-under detection
OVER_UNDER_MAX_GAP_Y = 0.012       # tune
OVER_UNDER_MIN_X_OVERLAP = 0.65    # tune

# Lexical anchors (boost only)
CREDITS_ROLE_ANCHORS = [
  "directed by", "written by", "screenplay by", "story by",
  "produced by", "executive producer", "executive producers",
  "director of photography", "production designer",
  "music by", "edited by", "casting by",
  "based on", "a film by"
]
```

---

## 4. Algorithm Spec

### 4.1 Inputs

- `line_regions: List[LineRegion]` (existing OCR output)
- `original_image_bytes` (full-res upload; already cached per job per control doc) fileciteturn0file0

### 4.2 Step A — Select candidate band

1. Filter `line_regions` by `center_norm.y` into bottom band.
2. If bottom band yields no viable candidates, optionally repeat for top-lite band.

### 4.3 Step B — Pass 1: detect overlays and preserve them

For each region in the band, tag as overlay if **any**:

**(B1) URL/social signature**

- text contains `@` → `SOCIAL_HANDLE`
- text contains a likely domain token (`.` plus plausible TLD-ish pattern) → `URL`

**(B2) Badge/logo geometry**

- compute approximate axis-aligned bbox (if not present) from quad
- area_norm = width_norm \* height_norm
- if area_norm < OVERLAY_AREA_SMALL → `LOGO` or `UNKNOWN`
- if height_norm < OVERLAY_HEIGHT_TINY and (width/height) > OVERLAY_ASPECT_WIDE → `UNKNOWN` or `LOGO`
- if text matches common rating patterns (optional) → `RATING_BADGE`

Output:

- `overlays: List[CreditsOverlayElement]` (preserve geometry + text)
- `residual_regions: List[LineRegion]` (band regions not tagged as overlay)

### 4.4 Step C — Pass 2: cluster residual regions into dense blobs

Cluster residual regions in geometry space. Use a simple, deterministic approach:

1. Sort by y, then x.
2. Build clusters greedily where adjacent regions are close in y and overlap in x-range.
   - y adjacency: abs(y_i - y_j) < dy_threshold (tune; start ~0.02)
   - x overlap: overlap_ratio > 0.2 (tune)
3. Track per-cluster stats:
   - line_count
   - median font_height_norm (from quad height)
   - angle mean/std
   - cluster bbox/area
   - “density”: line_count / cluster_height

### 4.5 Step D — Score clusters as credits candidates

Score each cluster; pick the highest.

Recommended scoring components (weights tuneable, start simple):

- +1.0 if line_count >= CREDITS_LINE_COUNT_MIN
- +1.0 if median_font_height <= CREDITS_FONT_HEIGHT_MAX
- +1.0 if density above threshold
- +0.5 if cluster centroid in bottom-most quartile of band
- +0.5 if angle_std <= CREDITS_ANGLE_STD_MAX
- +0.0–1.0 lexical boost: fraction of lines matching any `CREDITS_ROLE_ANCHORS` (casefold)

**Lexical boost is never required**; it only increases confidence.

If best score < minimal acceptance threshold → no credits block detected.

### 4.6 Step E — Compute oriented bbox (quad) for the winning cluster

1. Determine dominant angle (mean/median of region angles).
2. Rotate all quad vertices by `-dominant_angle` around image center (or simply in normalized space).
3. Take min/max x/y to form axis-aligned bbox in rotated space.
4. Rotate bbox corners back to original angle to create `quad_norm`.

Set `CreditsBlock.geometry` accordingly; also compute `bbox_norm` for convenience.

### 4.7 Step F — Crop high-res credits image from original upload

Crop using the oriented bbox with small padding (e.g., 1–2% of bbox size).

Implementation detail:

- If full oriented crop is complex, you may do:
  - rotate image to align bbox (dominant angle) → axis-aligned crop → rotate back (optional)
- Minimum acceptable: axis-aligned crop using bbox_norm (less ideal, but ok for first iteration)  
  _If you do axis-aligned crop first, log that it is axis-aligned and track as a known limitation._

### 4.8 Step G — Specialized OCR + grouping inside the crop

Run OCR on cropped image (same provider), then:

1. Reconstruct lines (reuse existing rotation-aware line reconstruction)
2. Compute `font_height_norm` per line relative to crop height
3. Create preliminary `CreditLine`s
4. Detect **over/under** structures:
   - if a small-font line sits directly above a larger-font line
   - vertical gap <= OVER_UNDER_MAX_GAP_Y
   - x overlap >= OVER_UNDER_MIN_X_OVERLAP
   - emit as two-line CreditGroup (preferred) or two stacked groups
5. Classify groups:
   - `CERTIFICATION`: tokens like `A.C.E.`/`ASC` patterns (all caps, periods, short)
   - `TITLE`: contains role anchors (“directed by”, “produced by”, etc.)
   - `PROPER_NAME`: mostly capitalized words, name-like patterns, no role anchors
   - else `UNKNOWN`

Set `localizable`:

- True only for `TITLE` groups
- False for others

**Optional LLM assist (only after heuristics):**

- If classification confidence low, send _group text only_ (not full OCR) to an LLM classifier to label as TITLE/NAME/CERTIFICATION.
- Keep this behind a feature flag/env var so it can be disabled during debugging.

---

## 5. Logging / Observability (must-have)

Follow the project’s “logging is first-class” expectation. fileciteturn0file0

Emit logs (INFO or DEBUG as appropriate):

### 5.1 Pass 1 logs

- `CreditsPass1Start job_id=... band=BOTTOM_BAND`
- `CreditsOverlaysDetected counts_by_type={...} total=...`

### 5.2 Pass 2 logs

- `CreditsPass2ClustersScored top_k=[{score,line_count,median_font_height,angle_std,lex_boost,bbox_norm}...]`
- `CreditsBlockSelected score=... confidence=... bbox_norm=... angle=...`

### 5.3 Crop + OCR logs

- `CreditsCropExtracted method=oriented|axis_aligned crop_px_w=... crop_px_h=...`
- `CreditsOcrSummary lines=... median_font_height=... angle=...`
- `CreditsOcrPreview first_lines=[...]` (first N lines)

### 5.4 Grouping logs

- `CreditsGroupingSummary groups_total=... by_type={TITLE:..,PROPER_NAME:..,CERTIFICATION:..,UNKNOWN:..}`
- If over/under detected: `CreditsOverUnderDetected pairs=...`

---

## 6. Tests (pytest)

Add backend unit tests for deterministic behavior:

1. **Overlay detection**
   - Given synthetic LineRegions including an URL-like region, ensure it becomes an overlay and is preserved with geometry.

2. **Cluster scoring**
   - Given a set of small-font, many-line regions in bottom band, ensure credits block is detected and has confidence > threshold.

3. **Lexical boost**
   - Ensure presence of “directed by” increases score but does not block detection when absent.

4. **Over/under grouping**
   - Given two lines with font height difference and close vertical gap + x overlap, ensure they become a two-line CreditGroup.

Tests should not require real Google Vision calls; create minimal synthetic geometry objects.

---

## 7. Implementation Plan (small commits)

Use conventional commits and keep changes focused. fileciteturn0file3

### Commit 1 — models

- Add `models/credits.py` with Pydantic models (above).
- Add minimal helpers for bbox/area/font_height from quad.

### Commit 2 — pass 1 overlays

- Implement `detect_credits_overlays(line_regions, band_bbox)` returning overlays + residuals.
- Add logs + unit tests.

### Commit 3 — pass 2 clustering + scoring

- Implement `detect_credits_block(residual_regions, overlays, band_bbox)`:
  - clustering
  - scoring
  - oriented bbox
- Add logs + unit tests.

### Commit 4 — crop + specialized OCR hook (stub OK)

- Add `extract_credits_crop(original_image_bytes, credits_block_geometry)`:
  - axis-aligned crop first if needed
- Add pipeline hook to call existing OCR on crop (can be behind flag).
- Log crop method.

### Commit 5 — credits grouping

- Implement grouping rules and output `credit_groups`.
- Add logs + unit tests.

---

## 8. Cursor Prompt (copy/paste)

> **Task:** Implement Credits Block Detection & Semantic Grouping exactly per this spec.  
> **Inputs:** Load control docs: ControlDocsInfo.md, ChatGPT_Control.md (Appendix A), FuncTechSpec.md, API_Definition.md, CodingStandards.md. fileciteturn0file5 fileciteturn0file0 fileciteturn0file1 fileciteturn0file2 fileciteturn0file3  
> **Constraints:** No breaking API changes; logging-first; preserve overlays; lexical anchors are boost-only.  
> **Process:** Implement in 5 small commits (models → overlays → clustering/scoring → crop hook → grouping), with pytest tests each step, and update DevProgress accordingly.

---

## 9. Notes / Known Limitations Allowed in First Iteration

- Oriented crop may be approximated by axis-aligned bbox crop initially (must be logged as such).
- Rating badge detection can be coarse; better classification can come later.
- LLM assist is optional and must be behind a flag; start with heuristics.
