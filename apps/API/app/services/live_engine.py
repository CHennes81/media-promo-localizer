"""
Live localization engine using real OCR and translation providers.

This engine implements the full pipeline with real external services:
- OCR: Google Cloud Vision (or other configured provider)
- Translation: OpenAI (or other LLM)
- Inpainting: Stub (deferred per FuncTechSpec out-of-scope)
"""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from app.clients.inpainting_client import StubInpaintingClient
from app.clients.interfaces import IOcrClient, IInpaintingClient, ITranslationClient
from app.clients.ocr_client import CloudOcrClient
from app.clients.translation_client import LlmTranslationClient
from app.models import (
    DetectedText,
    ErrorInfo,
    JobResult,
    JobStatus,
    LocalizationJob,
    ProcessingTimeMs,
    Progress,
    ProgressStage,
)

logger = logging.getLogger("media_promo_localizer")


class LiveLocalizationEngine:
    """Live localization engine using real providers."""

    def __init__(
        self,
        ocr_client: IOcrClient,
        translation_client: ITranslationClient,
        inpainting_client: IInpaintingClient,
    ):
        """
        Initialize live localization engine.

        Args:
            ocr_client: OCR client implementation
            translation_client: Translation client implementation
            inpainting_client: Inpainting client implementation (stub for now)
        """
        self.ocr_client = ocr_client
        self.translation_client = translation_client
        self.inpainting_client = inpainting_client

    async def run(self, job: LocalizationJob) -> LocalizationJob:
        """
        Run the live localization pipeline.

        Args:
            job: LocalizationJob to process

        Returns:
            Updated LocalizationJob with result or error
        """
        try:
            job.status = JobStatus.PROCESSING
            job.updatedAt = datetime.now(timezone.utc)

            # Load image file
            if not job.filePath:
                raise ValueError("Job filePath is required")
            image_path = Path(job.filePath)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {job.filePath}")

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # Stage 1: OCR
            logger.info(f"JobStarted jobId={job.jobId} stage=OCR")
            ocr_start = time.perf_counter()
            try:
                ocr_result = await self.ocr_client.recognize_text(image_bytes)
                ocr_time_ms = max(1, int((time.perf_counter() - ocr_start) * 1000))

                # Classify text regions by role (simple heuristic for now)
                # In future, this could use an LLM for more sophisticated classification
                classified_regions = self._classify_text_regions(ocr_result.text_regions)

                job.progress = Progress(
                    stage=ProgressStage.OCR,
                    percent=25,
                    stageTimingsMs={"ocr": ocr_time_ms},
                )
                job.updatedAt = datetime.now(timezone.utc)
                logger.info(
                    f"JobUpdated jobId={job.jobId} stage=OCR durationMs={ocr_time_ms} "
                    f"regions={len(classified_regions)}"
                )
            except Exception as e:
                logger.error(f"OCR failed for job {job.jobId}: {e}", exc_info=True)
                job.status = JobStatus.FAILED
                job.error = ErrorInfo(
                    code="OCR_MODEL_ERROR",
                    message=f"OCR processing failed: {str(e)}",
                    retryable=True,
                )
                job.updatedAt = datetime.now(timezone.utc)
                return job

            # Stage 2: Translation
            logger.info(f"JobUpdated jobId={job.jobId} stage=TRANSLATION")
            translation_start = time.perf_counter()
            try:
                # Filter to only localizable regions (per policy)
                localizable_regions = [
                    r for r in classified_regions if self._is_localizable(r)
                ]

                translated_regions = await self.translation_client.translate_text_regions(
                    localizable_regions, job.targetLanguage
                )

                translation_time_ms = max(1, int((time.perf_counter() - translation_start) * 1000))

                job.progress = Progress(
                    stage=ProgressStage.TRANSLATION,
                    percent=50,
                    stageTimingsMs={
                        "ocr": ocr_time_ms,
                        "translation": translation_time_ms,
                    },
                )
                job.updatedAt = datetime.now(timezone.utc)
                logger.info(
                    f"JobUpdated jobId={job.jobId} stage=TRANSLATION "
                    f"durationMs={translation_time_ms} translated={len(translated_regions)}"
                )
            except Exception as e:
                logger.error(
                    f"Translation failed for job {job.jobId}: {e}", exc_info=True
                )
                job.status = JobStatus.FAILED
                job.error = ErrorInfo(
                    code="TRANSLATION_MODEL_ERROR",
                    message=f"Translation processing failed: {str(e)}",
                    retryable=True,
                )
                job.updatedAt = datetime.now(timezone.utc)
                return job

            # Stage 3: Inpainting (stub - returns original image)
            logger.info(f"JobUpdated jobId={job.jobId} stage=INPAINT")
            inpaint_start = time.perf_counter()
            try:
                # Use stub inpainting (returns original image)
                inpainted_image_bytes = await self.inpainting_client.inpaint_regions(
                    image_bytes, classified_regions
                )
                inpaint_time_ms = max(1, int((time.perf_counter() - inpaint_start) * 1000))

                job.progress = Progress(
                    stage=ProgressStage.INPAINT,
                    percent=75,
                    stageTimingsMs={
                        "ocr": ocr_time_ms,
                        "translation": translation_time_ms,
                        "inpaint": inpaint_time_ms,
                    },
                )
                job.updatedAt = datetime.now(timezone.utc)
                logger.info(
                    f"JobUpdated jobId={job.jobId} stage=INPAINT durationMs={inpaint_time_ms}"
                )
            except Exception as e:
                logger.error(
                    f"Inpainting failed for job {job.jobId}: {e}", exc_info=True
                )
                job.status = JobStatus.FAILED
                job.error = ErrorInfo(
                    code="INPAINT_MODEL_ERROR",
                    message=f"Inpainting processing failed: {str(e)}",
                    retryable=True,
                )
                job.updatedAt = datetime.now(timezone.utc)
                return job

            # Stage 4: Packaging (save output image and prepare result)
            logger.info(f"JobUpdated jobId={job.jobId} stage=PACKAGING")
            packaging_start = time.perf_counter()

            # Save output image (for now, just copy original since inpainting is stubbed)
            # In future, this would render translated text onto the inpainted image
            output_dir = image_path.parent
            output_path = output_dir / "output.png"
            with open(output_path, "wb") as f:
                f.write(inpainted_image_bytes)

            # Build detected text list for result (mix of original and translated)
            detected_text_list: list[DetectedText] = []
            for region in classified_regions:
                # Find translation if available
                translated = next(
                    (tr for tr in translated_regions if tr.original_text == region.text),
                    None,
                )
                text_to_show = (
                    translated.translated_text if translated else region.text
                )
                detected_text_list.append(
                    DetectedText(
                        text=text_to_show,
                        boundingBox=region.boundingBox,
                        role=region.role,
                    )
                )

            packaging_time_ms = max(1, int((time.perf_counter() - packaging_start) * 1000))
            total_time_ms = (
                ocr_time_ms + translation_time_ms + inpaint_time_ms + packaging_time_ms
            )

            job.progress = Progress(
                stage=ProgressStage.PACKAGING,
                percent=100,
                stageTimingsMs={
                    "ocr": ocr_time_ms,
                    "translation": translation_time_ms,
                    "inpaint": inpaint_time_ms,
                    "packaging": packaging_time_ms,
                },
            )
            job.updatedAt = datetime.now(timezone.utc)

            # Generate result
            job.result = JobResult(
                imageUrl=f"/static/jobs/{job.jobId}/output.png",
                thumbnailUrl=f"/static/jobs/{job.jobId}/thumb.png",
                processingTimeMs=ProcessingTimeMs(
                    ocr=ocr_time_ms,
                    translation=translation_time_ms,
                    inpaint=inpaint_time_ms,
                    total=total_time_ms,
                ),
                language=job.targetLanguage,
                sourceLanguage=job.sourceLanguage or "en-US",
                detectedText=detected_text_list,
            )

            job.status = JobStatus.SUCCEEDED
            job.updatedAt = datetime.now(timezone.utc)
            logger.info(
                f"JobCompleted jobId={job.jobId} status=succeeded durationMs={total_time_ms}"
            )

            return job

        except Exception as e:
            logger.error(f"JobFailed jobId={job.jobId} error={str(e)}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error = ErrorInfo(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred during processing.",
                retryable=True,
            )
            job.updatedAt = datetime.now(timezone.utc)
            return job

    def _classify_text_regions(self, regions: list[DetectedText]) -> list[DetectedText]:
        """
        Classify text regions by semantic role using simple heuristics.

        Args:
            regions: List of detected text regions

        Returns:
            List of regions with updated role classifications
        """
        classified = []
        for region in regions:
            text_upper = region.text.upper()
            role = region.role

            # Simple heuristics for role classification
            if any(
                keyword in text_upper
                for keyword in ["COMING SOON", "NOW PLAYING", "IN THEATERS"]
            ):
                role = "tagline"
            elif any(keyword in text_upper for keyword in ["DIRECTED BY", "PRODUCED BY"]):
                role = "credits"
            elif "HTTP" in text_upper or "WWW." in text_upper or "@" in text_upper:
                role = "other"  # URLs/social handles - locked
            elif len(text_upper) > 30:
                # Likely a title if it's long
                role = "title"
            elif len(text_upper) < 10 and any(c.isdigit() for c in text_upper):
                # Likely a date or rating
                role = "other"

            classified.append(DetectedText(text=region.text, boundingBox=region.boundingBox, role=role))

        return classified

    def _is_localizable(self, region: DetectedText) -> bool:
        """
        Determine if a text region should be localized based on policy.

        Args:
            region: Text region to check

        Returns:
            True if region should be localized, False if locked
        """
        # Per FuncTechSpec: URLs, social handles, rating badges are locked
        text_upper = region.text.upper()
        if "HTTP" in text_upper or "WWW." in text_upper or "@" in text_upper:
            return False

        # Per spec: titles are locked by default (configurable per market/script in future)
        if region.role == "title":
            return False

        # Credits: roles localizable, names preserved (simplified for now)
        if region.role == "credits":
            return True  # Will need more sophisticated logic later

        # Taglines and other text: localizable
        return True


def create_live_engine(
    ocr_api_key: str,
    ocr_api_endpoint: str | None,
    openai_api_key: str,
    translation_model: str,
) -> LiveLocalizationEngine:
    """
    Factory function to create a LiveLocalizationEngine with configured clients.

    Args:
        ocr_api_key: OCR provider API key
        ocr_api_endpoint: Optional OCR API endpoint
        openai_api_key: OpenAI API key
        translation_model: Translation model name

    Returns:
        Configured LiveLocalizationEngine instance
    """
    ocr_client = CloudOcrClient(api_key=ocr_api_key, api_endpoint=ocr_api_endpoint)
    translation_client = LlmTranslationClient(api_key=openai_api_key, model=translation_model)
    inpainting_client = StubInpaintingClient()

    return LiveLocalizationEngine(
        ocr_client=ocr_client,
        translation_client=translation_client,
        inpainting_client=inpainting_client,
    )

