"""
Inpainting client implementations.

Note: Full background inpainting is out of scope for Sprint 3 - Batch 1.
This is a stub implementation that returns the original image unchanged.
Future batches will implement actual background removal/inpainting.
"""
import asyncio
import logging
import time
from typing import List, Optional

from app.clients.interfaces import IInpaintingClient
from app.models.jobs import DetectedText

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
        job_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bytes:
        """
        Stub implementation: returns original image unchanged.

        Args:
            image_bytes: Original image bytes
            regions: List of text regions to inpaint (ignored in stub)
            job_id: Optional job ID for logging context
            request_id: Optional request ID for logging context

        Returns:
            Original image bytes (unchanged)
        """
        # Log stub service call
        endpoint_base = "stub://inpainting"
        outbound_timestamp = time.time()
        correlation = []
        if request_id:
            correlation.append(f"request={request_id}")
        if job_id:
            correlation.append(f"job={job_id}")
        correlation_str = " ".join(correlation) if correlation else ""

        logger.info(
            f"ServiceCall {correlation_str} service=INPAINTING endpoint={endpoint_base} "
            f"method=STUB outbound_timestamp={outbound_timestamp:.3f} "
            f"payloadSizeBytes={len(image_bytes)} regions={len(regions)}"
        )

        # Simulate stub processing time
        call_start = time.perf_counter()
        await asyncio.sleep(0.001)  # Minimal delay for stub
        call_duration_ms = int((time.perf_counter() - call_start) * 1000)
        response_timestamp = time.time()

        # Log stub response
        logger.info(
            f"ServiceResponse {correlation_str} service=INPAINTING status=200 "
            f"response_timestamp={response_timestamp:.3f} durationMs={call_duration_ms} "
            f"responseSizeBytes={len(image_bytes)} stub=true"
        )

        # Return original image - no inpainting performed
        return image_bytes
