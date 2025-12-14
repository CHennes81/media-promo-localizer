"""
OCR client implementations.
"""
import base64
import logging
import math
import time
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import httpx
from PIL import Image

from app.clients.interfaces import IOcrClient, OcrResult
from app.models import DetectedText

logger = logging.getLogger("media_promo_localizer")

# Type alias for word data tuple: (text, x1, y1, x2, y2, height, vertices_norm, angle_deg)
WordData = Tuple[str, float, float, float, float, float, Optional[List[Tuple[float, float]]], float]


class CloudOcrClient(IOcrClient):
    """Google Cloud Vision API OCR client."""

    def __init__(self, api_key: str, api_endpoint: Optional[str] = None):
        """
        Initialize Google Cloud Vision OCR client.

        Args:
            api_key: Google Cloud Vision API key
            api_endpoint: Optional custom API endpoint (defaults to Google's)
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint or "https://vision.googleapis.com/v1/images:annotate"
        if not self.api_key:
            raise ValueError("OCR_API_KEY is required for live OCR mode")

    async def recognize_text(
        self, image_bytes: bytes, job_id: Optional[str] = None, request_id: Optional[str] = None
    ) -> OcrResult:
        """
        Recognize text in an image using Google Cloud Vision API.

        Args:
            image_bytes: Image file bytes (JPG/PNG)
            job_id: Optional job ID for logging context

        Returns:
            OcrResult with detected text regions and image dimensions

        Raises:
            Exception: If OCR processing fails
        """
        # Log endpoint (without API key)
        endpoint_base = self.api_endpoint.split("?")[0] if "?" in self.api_endpoint else self.api_endpoint
        outbound_timestamp = time.time()
        correlation = []
        if request_id:
            correlation.append(f"request={request_id}")
        if job_id:
            correlation.append(f"job={job_id}")
        correlation_str = " ".join(correlation) if correlation else ""

        logger.info(
            f"ServiceCall {correlation_str} service=OCR endpoint={endpoint_base} "
            f"method=POST outbound_timestamp={outbound_timestamp:.3f} "
            f"payloadSizeBytes={len(image_bytes)}"
        )

        try:
            # Get image dimensions
            image = Image.open(BytesIO(image_bytes))
            image_width, image_height = image.size

            # Prepare request for Google Cloud Vision API
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # Use DOCUMENT_TEXT_DETECTION for better hierarchy (pages → blocks → paragraphs → words)
            request_body = {
                "requests": [
                    {
                        "image": {"content": image_base64},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    }
                ]
            }

            # Call Google Cloud Vision API
            call_start = time.perf_counter()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_endpoint}?key={self.api_key}",
                    json=request_body,
                )
                call_duration_ms = int((time.perf_counter() - call_start) * 1000)
                response_timestamp = time.time()
                status_code = response.status_code

                # Get response size
                response_size = len(response.content) if hasattr(response, "content") else 0

                # Log response
                logger.info(
                    f"ServiceResponse {correlation_str} service=OCR status={status_code} "
                    f"response_timestamp={response_timestamp:.3f} durationMs={call_duration_ms} "
                    f"responseSizeBytes={response_size}"
                )

                response.raise_for_status()
                result = response.json()

            # Parse response using documentTextDetection hierarchy (pages → blocks → paragraphs → words)
            # Word structure: (text, x1, y1, x2, y2, height, vertices_norm, angle_deg)
            words: List[WordData] = []

            if "responses" in result and len(result["responses"]) > 0:
                response = result["responses"][0]

                # Prefer documentTextDetection hierarchy if available
                if "fullTextAnnotation" in response and "pages" in response["fullTextAnnotation"]:
                    pages = response["fullTextAnnotation"]["pages"]
                    for page in pages:
                        if "blocks" in page:
                            for block in page["blocks"]:
                                if "paragraphs" in block:
                                    for paragraph in block["paragraphs"]:
                                        if "words" in paragraph:
                                            for word in paragraph["words"]:
                                                word_data = self._extract_word_data(
                                                    word, image_width, image_height
                                                )
                                                if word_data:
                                                    words.append(word_data)

                # Fallback to textAnnotations if documentTextDetection not available
                if not words and "textAnnotations" in response:
                    # First annotation is the full text; skip it
                    for i, annotation in enumerate(response["textAnnotations"]):
                        if i == 0:
                            continue  # Skip full text annotation

                        if "boundingPoly" in annotation and "vertices" in annotation["boundingPoly"]:
                            vertices = annotation["boundingPoly"]["vertices"]
                            word_data = self._extract_word_from_vertices(
                                annotation.get("description", "").strip(),
                                vertices,
                                image_width,
                                image_height,
                            )
                            if word_data:
                                words.append(word_data)

            # Group words into lines using rotation-aware clustering
            text_regions = self._group_words_into_lines_rotation_aware(words)

            logger.info(
                f"[OCR] Summary: words={len(words)} reconstructed_lines={len(text_regions)}"
            )

            # Log first N line regions
            for i, region in enumerate(text_regions[:10]):
                # Extract geometry if available (stored in a custom attribute)
                geometry_info = ""
                if hasattr(region, "_geometry"):
                    geom = region._geometry
                    angle = geom.get("angle_deg", 0)
                    center = geom.get("center_norm", {})
                    center_str = f"{center.get('x', 0):.3f},{center.get('y', 0):.3f}" if center else "N/A"
                    geometry_info = f" angle_deg={angle:.1f} center_norm={center_str}"

                text_preview = region.text[:120] + "..." if len(region.text) > 120 else region.text
                logger.info(
                    f"[OCR] LineRegion id={i} role={region.role}{geometry_info} "
                    f"text={text_preview!r}"
                )
            return OcrResult(
                text_regions=text_regions,
                image_width=image_width,
                image_height=image_height,
            )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            response_timestamp = time.time()
            logger.error(
                f"ServiceResponse {correlation_str} service=OCR status={status_code} "
                f"response_timestamp={response_timestamp:.3f} error=HTTPStatusError",
                exc_info=True,
            )
            raise Exception(f"OCR service returned error: {status_code}")
        except httpx.TimeoutException:
            response_timestamp = time.time()
            logger.error(
                f"ServiceResponse {correlation_str} service=OCR status=504 "
                f"response_timestamp={response_timestamp:.3f} error=TimeoutException",
                exc_info=True,
            )
            raise Exception("OCR service timeout")
        except Exception as e:
            response_timestamp = time.time()
            logger.error(
                f"ServiceResponse {correlation_str} service=OCR status=500 "
                f"response_timestamp={response_timestamp:.3f} error={type(e).__name__}",
                exc_info=True,
            )
            raise Exception(f"OCR processing failed: {str(e)}")

    def _extract_word_data(
        self, word: Dict, image_width: int, image_height: int
    ) -> Optional[WordData]:
        """
        Extract word data from Vision API word object.

        Returns:
            Tuple of (text, x1, y1, x2, y2, height, vertices_norm, angle_deg) or None
        """
        # Extract text from word symbols
        symbols = word.get("symbols", [])
        if not symbols:
            return None

        text_parts = []
        for symbol in symbols:
            text_parts.append(symbol.get("text", ""))
        text = "".join(text_parts).strip()
        if not text:
            return None

        # Extract bounding box vertices
        bounding_box = word.get("boundingBox", {})
        vertices = bounding_box.get("vertices", [])
        if not vertices or len(vertices) < 4:
            return None

        return self._extract_word_from_vertices(text, vertices, image_width, image_height)

    def _extract_word_from_vertices(
        self, text: str, vertices: List[Dict], image_width: int, image_height: int
    ) -> Optional[WordData]:
        """
        Extract word data from vertices list.

        Returns:
            Tuple of (text, x1, y1, x2, y2, height, vertices_norm, angle_deg)
        """
        # Extract and normalize vertices
        vertex_list = []
        for v in vertices:
            x = v.get("x", 0)
            y = v.get("y", 0)
            vertex_list.append((x / image_width, y / image_height))

        if len(vertex_list) < 4:
            return None

        # Normalize vertex order to TL, TR, BR, BL
        vertices_norm = self._normalize_vertex_order(vertex_list)

        # Compute axis-aligned bounding box
        x_coords = [v[0] for v in vertices_norm]
        y_coords = [v[1] for v in vertices_norm]
        x1 = max(0.0, min(1.0, min(x_coords)))
        y1 = max(0.0, min(1.0, min(y_coords)))
        x2 = max(0.0, min(1.0, max(x_coords)))
        y2 = max(0.0, min(1.0, max(y_coords)))
        height = y2 - y1

        # Compute center and angle
        center_norm = (
            sum(v[0] for v in vertices_norm) / len(vertices_norm),
            sum(v[1] for v in vertices_norm) / len(vertices_norm),
        )

        # Compute angle from TL->TR vector
        tl = vertices_norm[0]
        tr = vertices_norm[1]
        angle_rad = math.atan2(tr[1] - tl[1], tr[0] - tl[0])
        angle_deg = math.degrees(angle_rad)

        return (text, x1, y1, x2, y2, height, vertices_norm, angle_deg)

    def _normalize_vertex_order(
        self, vertices: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Normalize vertex order to TL, TR, BR, BL.

        Strategy: sort by y then x to get top two and bottom two;
        within top pick left/right; within bottom pick right/left.
        """
        if len(vertices) != 4:
            # If not 4 vertices, return as-is (fallback)
            return vertices

        # Sort by y, then x
        sorted_vertices = sorted(vertices, key=lambda v: (v[1], v[0]))

        # Top two (smaller y)
        top = sorted_vertices[:2]
        top_sorted = sorted(top, key=lambda v: v[0])  # Left to right
        tl = top_sorted[0]
        tr = top_sorted[1] if len(top_sorted) > 1 else top_sorted[0]

        # Bottom two (larger y)
        bottom = sorted_vertices[2:]
        bottom_sorted = sorted(bottom, key=lambda v: v[0], reverse=True)  # Right to left
        br = bottom_sorted[0] if len(bottom_sorted) > 0 else bottom[0]
        bl = bottom_sorted[1] if len(bottom_sorted) > 1 else (bottom[0] if len(bottom) > 0 else vertices[2])

        return [tl, tr, br, bl]

    def _group_words_into_lines_rotation_aware(
        self, words: List[WordData]
    ) -> List[DetectedText]:
        """
        Group words into lines using rotation-aware center-based clustering.

        For each paragraph (or credits-band region):
        1. Compute dominant paragraph angle = median of word angles
        2. Rotate each word center around paragraph centroid by -dominant_angle
        3. Cluster words into lines using y' proximity
        4. Create line regions with rotation-aware geometry
        """
        if not words:
            return []

        # Group words into paragraphs (simple heuristic: words close together)
        paragraphs: List[List[WordData]] = []
        current_paragraph: List[WordData] = []

        # Sort words by y-coordinate
        words_sorted = sorted(words, key=lambda w: (w[2], w[1]))  # Sort by y1, then x1

        paragraph_y_threshold = 0.05  # 5% of image height for paragraph grouping

        for word in words_sorted:
            if not current_paragraph:
                current_paragraph.append(word)
            else:
                # Check if word is in same paragraph (vertical proximity)
                last_word_y = current_paragraph[-1][2]  # y1 of last word
                word_y = word[2]  # y1 of current word

                if abs(word_y - last_word_y) <= paragraph_y_threshold:
                    current_paragraph.append(word)
                else:
                    # Start new paragraph
                    if current_paragraph:
                        paragraphs.append(current_paragraph)
                    current_paragraph = [word]

        if current_paragraph:
            paragraphs.append(current_paragraph)

        # Process each paragraph
        all_line_regions: List[DetectedText] = []

        for para_words in paragraphs:
            if not para_words:
                continue

            # Compute dominant paragraph angle (median of word angles, ignoring outliers)
            angles = [w[7] for w in para_words if w[7] is not None]
            if not angles:
                dominant_angle = 0.0
            else:
                # Remove outliers (angles more than 45 degrees from median)
                angles_sorted = sorted(angles)
                median_angle = angles_sorted[len(angles_sorted) // 2]
                filtered_angles = [
                    a for a in angles
                    if abs(a - median_angle) <= 45.0
                ]
                if filtered_angles:
                    dominant_angle = sorted(filtered_angles)[len(filtered_angles) // 2]
                else:
                    dominant_angle = median_angle

            # Compute paragraph centroid
            para_centroid_x = sum((w[1] + w[3]) / 2 for w in para_words) / len(para_words)
            para_centroid_y = sum((w[2] + w[4]) / 2 for w in para_words) / len(para_words)

            # Rotate word centers around paragraph centroid
            word_rotated_data: List[Tuple[
                Tuple[str, float, float, float, float, float, Optional[List[Tuple[float, float]]], float],
                float, float  # rotated_y, original_center_y
            ]] = []

            angle_rad = math.radians(-dominant_angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)

            for word in para_words:
                word_center_x = (word[1] + word[3]) / 2
                word_center_y = (word[2] + word[4]) / 2

                # Translate to origin (paragraph centroid)
                dx = word_center_x - para_centroid_x
                dy = word_center_y - para_centroid_y

                # Rotate
                rotated_x = dx * cos_a - dy * sin_a
                rotated_y = dx * sin_a + dy * cos_a

                # Translate back
                rotated_y_abs = rotated_y + para_centroid_y

                word_rotated_data.append((word, rotated_y_abs, word_center_y))

            # Compute median word height for threshold
            heights = [w[5] for w in para_words]
            median_height = sorted(heights)[len(heights) // 2] if heights else 0.02

            # Cluster words into lines using rotated y-coordinate
            line_threshold = 0.6 * median_height

            lines: List[List[WordData]] = []

            # Sort by rotated y
            word_rotated_sorted = sorted(word_rotated_data, key=lambda w: w[1])

            for word_data in word_rotated_sorted:
                word, rotated_y, _ = word_data
                matched = False

                for line in lines:
                    if not line:
                        continue

                    # Compute line's rotated y center (average of rotated y's of words in line)
                    line_rotated_ys = []
                    for line_word in line:
                        # Find this word's rotated y
                        for wrd, ry, _ in word_rotated_data:
                            if wrd == line_word:
                                line_rotated_ys.append(ry)
                                break

                    if line_rotated_ys:
                        line_y_rotated = sum(line_rotated_ys) / len(line_rotated_ys)

                        if abs(rotated_y - line_y_rotated) <= line_threshold:
                            line.append(word)
                            matched = True
                            break

                if not matched:
                    lines.append([word])

            # Create line regions from clustered words
            for line_words in lines:
                if not line_words:
                    continue

                # Sort words in line by x-coordinate
                line_words_sorted = sorted(line_words, key=lambda w: w[1])

                # Collect all vertices from words in line
                all_vertices: List[Tuple[float, float]] = []
                for word in line_words_sorted:
                    if word[6]:  # vertices_norm
                        all_vertices.extend(word[6])

                # Compute line bounding box
                if all_vertices:
                    x_coords = [v[0] for v in all_vertices]
                    y_coords = [v[1] for v in all_vertices]
                    x1 = max(0.0, min(1.0, min(x_coords)))
                    y1 = max(0.0, min(1.0, min(y_coords)))
                    x2 = max(0.0, min(1.0, max(x_coords)))
                    y2 = max(0.0, min(1.0, max(y_coords)))
                else:
                    # Fallback to axis-aligned bbox
                    x1 = min(w[1] for w in line_words_sorted)
                    y1 = min(w[2] for w in line_words_sorted)
                    x2 = max(w[3] for w in line_words_sorted)
                    y2 = max(w[4] for w in line_words_sorted)

                # Compute line quad (approximate rotated rectangle)
                # Use axis-aligned bbox corners as quad (acceptable per spec)
                # Better implementation would project vertices into rotated space, take min/max, then unrotate
                quad_norm = [
                    {"x": x1, "y": y1},  # TL
                    {"x": x2, "y": y1},  # TR
                    {"x": x2, "y": y2},  # BR
                    {"x": x1, "y": y2},  # BL
                ]

                # Compute line center and angle
                line_center_x = (x1 + x2) / 2
                line_center_y = (y1 + y2) / 2
                center_norm = {"x": line_center_x, "y": line_center_y}

                # Use dominant angle for the line (or 0 if cannot compute)
                line_angle = dominant_angle if para_words else 0.0

                # Concatenate words with spaces
                line_text = " ".join(w[0] for w in line_words_sorted)

                # Create DetectedText with geometry stored in custom attribute
                region = DetectedText(
                    text=line_text,
                    boundingBox=[x1, y1, x2, y2],
                    role="other",
                )
                # Store geometry in custom attribute (will be extracted in live_engine)
                region._geometry = {
                    "quad_norm": quad_norm,
                    "center_norm": center_norm,
                    "angle_deg": line_angle,
                }

                all_line_regions.append(region)

        return all_line_regions

    def _group_words_into_lines(
        self, words: List[Tuple[str, float, float, float, float, float]]
    ) -> List[DetectedText]:
        """
        Group word-level annotations into single-line regions using vertical clustering.

        Args:
            words: List of (text, x1, y1, x2, y2, height) tuples in normalized coordinates

        Returns:
            List of DetectedText regions, one per line
        """
        if not words:
            return []

        # Sort words by y-coordinate (top to bottom)
        words_sorted = sorted(words, key=lambda w: (w[2], w[1]))  # Sort by y1, then x1

        # Group words into lines based on vertical overlap
        # Words are on the same line if their y-coordinates overlap significantly
        lines: List[List[Tuple[str, float, float, float, float, float]]] = []
        line_height_threshold = 0.02  # 2% of image height tolerance for line grouping

        for word in words_sorted:
            text, x1, y1, x2, y2, height = word
            word_center_y = (y1 + y2) / 2

            # Try to find an existing line this word belongs to
            matched = False
            for line in lines:
                if not line:
                    continue
                # Check if word's y-center is within the line's vertical range
                line_y_min = min(w[2] for w in line)  # min y1
                line_y_max = max(w[3] for w in line)  # max y2
                line_center_y = (line_y_min + line_y_max) / 2

                # If word center is close to line center (within threshold), add to line
                if abs(word_center_y - line_center_y) <= line_height_threshold:
                    line.append(word)
                    matched = True
                    break

            if not matched:
                # Start a new line
                lines.append([word])

        # Convert each line to a DetectedText region
        text_regions: List[DetectedText] = []
        for line_words in lines:
            if not line_words:
                continue

            # Compute tight bounding box around all words in the line
            x1 = min(w[1] for w in line_words)
            y1 = min(w[2] for w in line_words)
            x2 = max(w[3] for w in line_words)
            y2 = max(w[4] for w in line_words)

            # Concatenate words with spaces
            line_text = " ".join(w[0] for w in line_words)

            # Default role to "other" - will be classified later
            text_regions.append(
                DetectedText(
                    text=line_text,
                    boundingBox=[x1, y1, x2, y2],
                    role="other",
                )
            )

        return text_regions
