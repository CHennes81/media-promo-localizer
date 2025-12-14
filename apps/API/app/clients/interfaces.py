"""
Provider-agnostic interfaces for OCR, translation, and inpainting clients.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.jobs import DetectedText


class OcrResult:
    """Result from OCR processing."""

    def __init__(
        self,
        text_regions: List[DetectedText],
        image_width: int,
        image_height: int,
    ):
        """
        Initialize OCR result.

        Args:
            text_regions: List of detected text regions with normalized bounding boxes
            image_width: Original image width in pixels
            image_height: Original image height in pixels
        """
        self.text_regions = text_regions
        self.image_width = image_width
        self.image_height = image_height


class TranslatedRegion:
    """A text region with its translated text."""

    def __init__(
        self,
        original_text: str,
        translated_text: str,
        bounding_box: List[float],
        role: str,
    ):
        """
        Initialize translated region.

        Args:
            original_text: Original text content
            translated_text: Translated text content
            bounding_box: Normalized bounding box [x1, y1, x2, y2]
            role: Text role (title, tagline, credits, etc.)
        """
        self.original_text = original_text
        self.translated_text = translated_text
        self.bounding_box = bounding_box
        self.role = role


class IOcrClient(ABC):
    """Interface for OCR clients."""

    @abstractmethod
    async def recognize_text(self, image_bytes: bytes) -> OcrResult:
        """
        Recognize text in an image.

        Args:
            image_bytes: Image file bytes (JPG/PNG)

        Returns:
            OcrResult with detected text regions and image dimensions

        Raises:
            Exception: If OCR processing fails
        """
        pass


class ITranslationClient(ABC):
    """Interface for translation clients."""

    @abstractmethod
    async def translate_text_regions(
        self, regions: List[DetectedText], target_locale: str
    ) -> List[TranslatedRegion]:
        """
        Translate text regions to target locale.

        Args:
            regions: List of detected text regions to translate
            target_locale: Target locale code (BCP-47, e.g., "fr-FR")

        Returns:
            List of TranslatedRegion objects with translated text

        Raises:
            Exception: If translation fails
        """
        pass


class IInpaintingClient(ABC):
    """Interface for inpainting clients."""

    @abstractmethod
    async def inpaint_regions(
        self,
        image_bytes: bytes,
        regions: List[DetectedText],
    ) -> bytes:
        """
        Inpaint (remove) text regions from an image.

        Args:
            image_bytes: Original image bytes
            regions: List of text regions to inpaint (bounding boxes)

        Returns:
            Inpainted image bytes (same format as input)

        Raises:
            Exception: If inpainting fails
        """
        pass
