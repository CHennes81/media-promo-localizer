"""
OCR client implementations.
"""
import base64
import logging
import time
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import httpx
from PIL import Image

from app.clients.interfaces import IOcrClient, OcrResult
from app.models import DetectedText

logger = logging.getLogger("media_promo_localizer")


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

            request_body = {
                "requests": [
                    {
                        "image": {"content": image_base64},
                        "features": [{"type": "TEXT_DETECTION"}],
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

            # Parse response and extract word-level annotations, then group into lines
            words: List[Tuple[str, float, float, float, float, float]] = []  # (text, x1, y1, x2, y2, height)

            if "responses" in result and len(result["responses"]) > 0:
                annotations = result["responses"][0]
                if "textAnnotations" in annotations:
                    # First annotation is the full text; skip it
                    # Process individual word/block annotations
                    for i, annotation in enumerate(annotations["textAnnotations"]):
                        if i == 0:
                            continue  # Skip full text annotation

                        if "boundingPoly" in annotation and "vertices" in annotation["boundingPoly"]:
                            vertices = annotation["boundingPoly"]["vertices"]

                            # Extract bounding box coordinates
                            x_coords = [v.get("x", 0) for v in vertices]
                            y_coords = [v.get("y", 0) for v in vertices]

                            if x_coords and y_coords:
                                x1 = min(x_coords) / image_width
                                y1 = min(y_coords) / image_height
                                x2 = max(x_coords) / image_width
                                y2 = max(y_coords) / image_height
                                height = y2 - y1

                                # Normalize to [0, 1] range
                                x1 = max(0.0, min(1.0, x1))
                                y1 = max(0.0, min(1.0, y1))
                                x2 = max(0.0, min(1.0, x2))
                                y2 = max(0.0, min(1.0, y2))
                                height = max(0.0, min(1.0, height))

                                text = annotation.get("description", "").strip()
                                if text:
                                    words.append((text, x1, y1, x2, y2, height))

            # Group words into lines using vertical clustering
            text_regions = self._group_words_into_lines(words)

            logger.info(f"OCR detected {len(words)} words, grouped into {len(text_regions)} line regions")
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


