"""
Inpainting client implementations.

Note: Full background inpainting is out of scope for Sprint 3 - Batch 1.
This is a stub implementation that returns the original image unchanged.
Future batches will implement actual background removal/inpainting.
"""
import logging
from typing import List

from app.clients.interfaces import IInpaintingClient
from app.models import DetectedText

logger = logging.getLogger("media_promo_localizer")


class StubInpaintingClient(IInpaintingClient):
    """
    Stub inpainting client that returns the original image unchanged.

    Per FuncTechSpec §7 (Out-of-Scope Items), full background inpainting
    and complex compositing are deferred to future phases. This stub
    allows the pipeline to run end-to-end while preparing the interface
    for future implementation.
    """

    async def inpaint_regions(
        self,
        image_bytes: bytes,
        regions: List[DetectedText],
    ) -> bytes:
        """
        Stub implementation: returns original image unchanged.

        Args:
            image_bytes: Original image bytes
            regions: List of text regions to inpaint (ignored in stub)

        Returns:
            Original image bytes (unchanged)
        """
        logger.info(
            f"Inpainting stub: returning original image unchanged "
            f"(would inpaint {len(regions)} regions in future implementation)"
        )
        # Return original image - no inpainting performed
        return image_bytes

