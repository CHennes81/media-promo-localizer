You are working as a senior engineer in the `media-promo-localizer` repo.

Operate in **IMPLEMENTATION_MODE**: you may modify application code and add new tests, but you may NOT change existing test expectations unless it is strictly necessary to align with the current FuncTechSpec and control docs.

## Goal of this batch (Sprint 3 – Batch 2)

Improve the **live OCR + debug + UI** experience so that:

- OCR output is represented as **per-line text regions** (especially for the credits band).
- Each region includes: normalized bounding box, role, original text, translated text (when available), and a localizability flag.
- The backend returns a structured **`debug` payload** with these regions and emits matching log messages.
- All log messages are written to **both stdout and a logfile on disk**.
- The frontend result view shows:
  - A single large **localized poster** image (not side-by-side with original).
  - Existing **timing metrics**.
  - A **Details** dialog showing all debug regions in a table.
  - A **Show OCR Boxes** toggle that overlays **purple bounding boxes for ALL regions** on the localized image.

## Control docs to respect

Before coding, skim and follow:

- `artifacts/FuncTechSpec.md`
- `artifacts/DevProcess.md`
- `artifacts/DevPlan.md`
- `artifacts/DevChecklist_Sprint3.md` (add / mark a Batch 2 section if needed)
- `artifacts/coding/CodingStandards.md`
- `artifacts/CommitGuide.md`

Do NOT modify CI configs, Husky hooks, or other artifacts unless explicitly required by this task.

---

## Part 1 – Backend: line-level OCR regions, debug payload, and logging

### 1.1 Line-level OCR model and grouping

1. Introduce / refine a model for a **single text region line** in the live pipeline. Name it something like `TextRegion` or `DebugTextRegion` (choose a clear name and put it with other pipeline models). Fields should include at least:
   - `id: str`
   - `role: Literal[...]` or `str` (e.g. `"title" | "tagline" | "credits" | "legal" | "other"`)
   - `bbox_norm`: normalized bounding box (x, y, width, height) in [0, 1] relative to the full image
   - `original_text: str`
   - `translated_text: Optional[str]` (to be populated after translation step)
   - `is_localizable: bool`

2. In the **Google Vision client** (`CloudOcrClient` or equivalent):
   - Parse the Vision response down to **word-level**.
   - Group words into **single-line regions** using Vision’s structural hints when available (paragraph/line metadata) and fall back to vertical clustering based on y-coordinate and height when necessary.
   - For each line:
     - Concatenate the words into a single `original_text` string (with reasonable spacing).
     - Compute a tight bounding box around all words in that line.
   - This grouping should apply to all text, not only credits.

3. Implement simple **role detection** on the line regions:
   - Keep any existing heuristics for `title`, `tagline`, etc.
   - Add heuristics to detect **credits** lines:
     - Lines near the **bottom** of the poster (normalized y above some threshold, e.g. > 0.75–0.80).
     - Wide bbox but small height (lots of small, compressed glyphs).
     - High density of characters.
   - Tag those lines with `role="credits"` (or whatever constant is already used for credits in the pipeline).

4. Ensure that, for a credits-heavy poster, the credits band is represented as **multiple line regions**, not a single giant region.

### 1.2 Debug payload in job result

1. Extend the job result model (for the live pipeline) to include a `debug` structure. For example:

   ```json
   "debug": {
     "regions": [ /* list of TextRegion */ ],
     "timings": { /* reuse existing per-step timings */ }
   }
   Use strongly-typed Pydantic models for debug and debug.regions.
   ```

In the live pipeline:

After OCR grouping, create the TextRegion list with original_text, role, bbox, and is_localizable.

After translation, populate translated_text for regions that were actually translated.

Attach this structure to the job’s response object.

Make sure the existing public API shape remains compatible with FuncTechSpec; debug can be additive / optional.

1.3 Logging to stdout and logfile
Configure Python logging (if not already done) so that:

There is a StreamHandler that logs to stdout.

There is a FileHandler (or RotatingFileHandler) that writes to a logfile on disk, e.g. logs/app.log in the backend project directory.

Both handlers share a reasonable log format (timestamp, level, logger name, message).

Follow existing project conventions if there is already a logging configuration module; otherwise create a small, clear configuration in an appropriate place (e.g. a logging.py or config/logging.py module) and initialize it on application startup.

Emit structured log messages at DEBUG level for each region:

After OCR grouping:

php-template
Copy code
[OCR] region id=<id> role=<role> bbox_norm=(x=<x>,y=<y>,w=<w>,h=<h>) text="<original_text>"
After translation (for regions that were processed):

bash
Copy code
[Xlate] region id=<id> role=<role> "<original_text>" -> "<translated_text>"
Ensure these messages go to both stdout and the logfile via the configured logging handlers.

Keep logging noise reasonable in production modes (e.g., use DEBUG for the most verbose messages).

Add or update backend tests as appropriate to cover:

The new debug payload shape.

The line-level grouping behavior (using mocked Vision responses).

Part 2 – Frontend: result layout, Details dialog, and purple OCR overlays
The current UI (based on the Star Trek screenshot) shows:

Large original poster at the top (upload area).

In the “Localization Complete” section: a side-by-side Original / Localized pair and timing metrics.

Adjust that as follows.

2.1 Result layout: single large localized image
In the “Localization Complete” card:

Remove the side-by-side “Original / Localized” thumbnails: the original poster remains visible in the upload area and does not need to be repeated.

Show a single large localized image:

Similar width/height treatment to the original preview at the top.

Responsive (constrain by width, maintain aspect ratio).

Keep the existing processing time cards (OCR, Translation, Inpaint, Packaging, Total).

Add:

A View Details button that opens a dialog containing debug information.

A Show OCR Boxes toggle (e.g., checkbox or switch) that controls whether purple OCR bounding boxes are rendered on the localized image.

2.2 Details dialog
Implement a dialog component (or reuse an existing one) that, when opened, displays a flat table of all debug regions from the job:

Source of data: debug.regions from the job API response.

Columns:

Role

BBox (normalized x, y, w, h) – display as a compact string.

Original text

Translated text (if any)

Localizable (boolean)

Include simple scrolling if there are many rows.

Handle empty or missing debug info gracefully (e.g., show a short “No debug data available for this job” message).

2.3 Purple OCR bounding-box overlays
When Show OCR Boxes is enabled:

Overlay a set of absolutely-positioned rectangles on top of the localized image.

Each rectangle corresponds to a debug.region:

Use the normalized bounding box (x, y, width, height) multiplied by the rendered image dimensions to position the overlay.

Style:

Visible purple border.

Semi-transparent fill is optional; use your judgment for clarity vs noise.

When the toggle is OFF, no overlays should be rendered.

Keep the implementation simple and robust; it does not need to be pixel-perfect but should clearly approximate the regions.

(Optional, nice-to-have, only if time allows):

When hovering a row in the Details dialog, highlight the corresponding box more strongly.

If implementing this is likely to introduce a lot of complexity, skip it for now; the base overlay behavior is the priority.

2.4 Frontend tests
Update or add tests to cover:

Presence of the single localized image in the result view.

Rendering of timing metrics as before.

That the Details dialog opens and shows at least one row when debug data exists.

Basic behavior of the Show OCR Boxes toggle (e.g., overlay elements present/absent).

Part 3 – Process, scope, and progress logging
Keep all changes scoped to:

The live pipeline / OCR / translation / debug models on the backend.

The main localization result view and related UI components on the frontend.

Logging configuration as needed.

Do NOT modify CI workflows, Husky, or unrelated artifacts.

After completing the work:

Update artifacts/DevProgress.md with a new entry for “Sprint 3 – Batch 2,” summarizing:

Backend OCR line grouping, debug payload, and logging changes.

Frontend result layout changes, Details dialog, and bounding-box overlay behavior.

If DevChecklist_Sprint3.md has or needs a Batch 2 section, mark tasks complete or add new items as appropriate.

Ensure all tests and linting pass for both backend and frontend before considering the batch done.

First, restate your understanding of this task and list the files you plan to touch. Then implement the changes in coherent steps, keeping diffs reviewable and aligned with the existing Coding Standards.
