"""
OCR client implementations.
"""
import base64
import logging
from io import BytesIO
from typing import List, Optional

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

    async def recognize_text(self, image_bytes: bytes) -> OcrResult:
        """
        Recognize text in an image using Google Cloud Vision API.

        Args:
            image_bytes: Image file bytes (JPG/PNG)

        Returns:
            OcrResult with detected text regions and image dimensions

        Raises:
            Exception: If OCR processing fails
        """
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_endpoint}?key={self.api_key}",
                    json=request_body,
                )
                response.raise_for_status()
                result = response.json()

            # Parse response and extract text regions
            text_regions: List[DetectedText] = []

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

                                # Normalize to [0, 1] range
                                x1 = max(0.0, min(1.0, x1))
                                y1 = max(0.0, min(1.0, y1))
                                x2 = max(0.0, min(1.0, x2))
                                y2 = max(0.0, min(1.0, y2))

                                text = annotation.get("description", "")
                                if text:
                                    # Default role to "other" - will be classified later
                                    text_regions.append(
                                        DetectedText(
                                            text=text,
                                            boundingBox=[x1, y1, x2, y2],
                                            role="other",
                                        )
                                    )

            logger.info(f"OCR detected {len(text_regions)} text regions")
            return OcrResult(
                text_regions=text_regions,
                image_width=image_width,
                image_height=image_height,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OCR API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OCR service returned error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("OCR API timeout")
            raise Exception("OCR service timeout")
        except Exception as e:
            logger.error(f"OCR processing failed: {e}", exc_info=True)
            raise Exception(f"OCR processing failed: {str(e)}")

