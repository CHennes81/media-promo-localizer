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
from app.clients.interfaces import IOcrClient, IInpaintingClient, ITranslationClient, TranslatedRegion
from app.clients.ocr_client import CloudOcrClient
from app.clients.translation_client import LlmTranslationClient
from app.config import settings
from app.models.jobs import (
    DebugInfo,
    DebugTextRegion,
    DetectedText,
    ErrorInfo,
    JobResult,
    JobStatus,
    LocalizationJob,
    ProcessingTimeMs,
    Progress,
    ProgressStage,
)
from app.utils.credits_detection import (
    detect_credits_band,
    extract_credits_crop,
    group_credits_lines,
)
from app.utils.image_cache import get_image_cache
from app.utils.image_derivatives import get_image_dimensions, maybe_make_derivative

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
        # Per-job derivative cache: (job_id, step, long_side_px) -> bytes
        self._derivative_cache: dict[tuple[str, str, int], bytes] = {}

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

            # Get original image bytes from cache or file
            image_cache = get_image_cache()
            original_image_bytes = image_cache.get_image(job.jobId)

            if original_image_bytes is None:
                # Fallback to file if not in cache
                if not job.filePath:
                    raise ValueError("Job filePath is required")
                image_path = Path(job.filePath)
                if not image_path.exists():
                    raise FileNotFoundError(f"Image file not found: {job.filePath}")
                with open(image_path, "rb") as f:
                    original_image_bytes = f.read()

                # Try to cache it for future use
                try:
                    width, height = get_image_dimensions(original_image_bytes)
                    image_cache.store_image(
                        job_id=job.jobId,
                        image_bytes=original_image_bytes,
                        width=width,
                        height=height,
                        content_type=None,
                    )
                except Exception as e:
                    logger.debug(f"Failed to cache image for job {job.jobId}: {e}")

            # Stage 1: OCR
            stage_name = "OCR"
            logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
            ocr_start = time.perf_counter()
            classified_regions: list[DetectedText] = []
            ocr_result = None
            ocr_time_ms = 0
            skipped = False

            if settings.SKIP_OCR:
                skipped = True
                logger.info(
                    f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                    f"reason=env_var env=SKIP_OCR value=true"
                )
                # Use empty list of text regions as OCR output
                classified_regions = []
                ocr_time_ms = max(1, int((time.perf_counter() - ocr_start) * 1000))
            else:
                try:
                    # Get OCR image bytes (derivative if needed)
                    ocr_image_bytes = self._get_image_for_step(
                        job.jobId, "OCR", original_image_bytes, settings.OCR_IMAGE_LONG_SIDE_PX
                    )

                    ocr_result = await self.ocr_client.recognize_text(
                        ocr_image_bytes, job_id=job.jobId
                    )
                    ocr_time_ms = max(1, int((time.perf_counter() - ocr_start) * 1000))

                    # Classify text regions by role (simple heuristic for now)
                    # In future, this could use an LLM for more sophisticated classification
                    classified_regions = self._classify_text_regions(ocr_result.text_regions)
                except Exception as e:
                    logger.error(f"OCR failed for job {job.jobId}: {e}", exc_info=True)
                    job.status = JobStatus.FAILED
                    job.error = ErrorInfo(
                        code="OCR_MODEL_ERROR",
                        message=f"OCR processing failed: {str(e)}",
                        retryable=True,
                    )
                    job.updatedAt = datetime.now(timezone.utc)
                    logger.info(
                        f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                        f"durationMs={ocr_time_ms} skipped={skipped}"
                    )
                    return job

            job.progress = Progress(
                stage=ProgressStage.OCR,
                percent=25,
                stageTimingsMs={"ocr": ocr_time_ms},
            )
            job.updatedAt = datetime.now(timezone.utc)
            logger.info(
                f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                f"durationMs={ocr_time_ms} skipped={skipped} regions={len(classified_regions)}"
            )

            # Credits detection (after OCR, before translation)
            credits_detection = None
            if not skipped and classified_regions and ocr_result is not None:
                try:
                    # Get image dimensions for credits detection
                    image_width = ocr_result.image_width
                    image_height = ocr_result.image_height

                    if image_width > 0 and image_height > 0:
                        credits_detection = detect_credits_band(
                            line_regions=ocr_result.text_regions,
                            original_image_bytes=original_image_bytes,
                            image_width=image_width,
                            image_height=image_height,
                            job_id=job.jobId,
                        )

                        # If credits block detected, extract crop and run specialized OCR + grouping
                        if (
                            credits_detection
                            and credits_detection.credits_block
                            and credits_detection.credits_block.geometry
                        ):
                            # Extract crop
                            crop_bytes, crop_method = extract_credits_crop(
                                original_image_bytes=original_image_bytes,
                                credits_block_geometry=credits_detection.credits_block.geometry,
                                image_width=image_width,
                                image_height=image_height,
                                job_id=job.jobId,
                            )

                            # Run OCR on crop
                            crop_ocr_result = await self.ocr_client.recognize_text(
                                crop_bytes, job_id=job.jobId
                            )

                            # Get crop dimensions
                            crop_width = crop_ocr_result.image_width
                            crop_height = crop_ocr_result.image_height

                            logger.info(
                                f"CreditsOcrSummary job={job.jobId} lines={len(crop_ocr_result.text_regions)} "
                                f"median_font_height=N/A angle={credits_detection.credits_block.dominant_angle_deg:.1f} "
                                f"crop_method={crop_method}"
                            )

                            # Log first N lines
                            preview_lines = [
                                r.text[:80] for r in crop_ocr_result.text_regions[:5]
                            ]
                            logger.info(
                                f"CreditsOcrPreview job={job.jobId} first_lines={preview_lines}"
                            )

                            # Group credits lines
                            credit_groups = group_credits_lines(
                                line_regions=crop_ocr_result.text_regions,
                                image_width=crop_width,
                                image_height=crop_height,
                                job_id=job.jobId,
                            )

                            # Update credits block with groups
                            credits_detection.credits_block.credit_groups = credit_groups

                except Exception as e:
                    # Log error but don't fail the job (credits detection is additive)
                    logger.warning(
                        f"CreditsDetectionError job={job.jobId} error={str(e)}", exc_info=True
                    )

            # Store credits detection in job
            if credits_detection:
                job.credits_detection = credits_detection.model_dump()

            # Stage 2: Translation
            stage_name = "TRANSLATION"
            logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
            translation_start = time.perf_counter()
            translated_regions: list[TranslatedRegion] = []
            translation_time_ms = 0
            skipped = False

            if settings.SKIP_TRANSLATION:
                skipped = True
                logger.info(
                    f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                    f"reason=env_var env=SKIP_TRANSLATION value=true"
                )
                # Set translated_text = original_text for all regions (identity translation)
                for region in classified_regions:
                    translated_regions.append(
                        TranslatedRegion(
                            original_text=region.text,
                            translated_text=region.text,
                            bounding_box=region.boundingBox,
                            role=region.role,
                        )
                    )
                translation_time_ms = max(1, int((time.perf_counter() - translation_start) * 1000))
            else:
                try:
                    # Filter to only localizable regions (per policy)
                    localizable_regions = [
                        r for r in classified_regions if self._is_localizable(r)
                    ]

                    translated_regions = await self.translation_client.translate_text_regions(
                        localizable_regions, job.targetLanguage
                    )

                    translation_time_ms = max(1, int((time.perf_counter() - translation_start) * 1000))
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
                    logger.info(
                        f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                        f"durationMs={translation_time_ms} skipped={skipped}"
                    )
                    return job

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
                f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                f"durationMs={translation_time_ms} skipped={skipped} translated={len(translated_regions)}"
            )

            # Stage 3: Inpainting (stub - returns original image)
            stage_name = "INPAINT"
            logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
            inpaint_start = time.perf_counter()
            inpainted_image_bytes = original_image_bytes
            inpaint_time_ms = 0
            skipped = False

            if settings.SKIP_INPAINT:
                skipped = True
                logger.info(
                    f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                    f"reason=env_var env=SKIP_INPAINT value=true"
                )
                # Pass through the original image bytes as the "localized" image
                inpainted_image_bytes = original_image_bytes
                inpaint_time_ms = max(1, int((time.perf_counter() - inpaint_start) * 1000))
            else:
                try:
                    # Get inpainting image bytes (derivative if needed)
                    inpaint_image_bytes = self._get_image_for_step(
                        job.jobId, "INPAINT", original_image_bytes, settings.INPAINT_IMAGE_LONG_SIDE_PX
                    )

                    # Use stub inpainting (returns original image)
                    inpainted_image_bytes = await self.inpainting_client.inpaint_regions(
                        inpaint_image_bytes, classified_regions
                    )
                    inpaint_time_ms = max(1, int((time.perf_counter() - inpaint_start) * 1000))
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
                    logger.info(
                        f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                        f"durationMs={inpaint_time_ms} skipped={skipped}"
                    )
                    return job

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
                f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                f"durationMs={inpaint_time_ms} skipped={skipped}"
            )

            # Stage 4: Packaging (save output image and prepare result)
            stage_name = "PACKAGING"
            logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
            packaging_start = time.perf_counter()
            packaging_time_ms = 0
            skipped = False

            if settings.SKIP_PACKAGING:
                skipped = True
                logger.info(
                    f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                    f"reason=env_var env=SKIP_PACKAGING value=true"
                )
                # Still return a valid job result object (use existing in-memory/localized image output as-is)
                packaging_time_ms = max(1, int((time.perf_counter() - packaging_start) * 1000))
            else:
                # Save output image (for now, just copy original since inpainting is stubbed)
                # In future, this would render translated text onto the inpainted image
                # Use original bytes for final output (not derivative)
                if job.filePath:
                    output_dir = Path(job.filePath).parent
                else:
                    output_dir = Path("tmp/uploads") / job.jobId
                output_path = output_dir / "output.png"
                with open(output_path, "wb") as f:
                    f.write(original_image_bytes)
                packaging_time_ms = max(1, int((time.perf_counter() - packaging_start) * 1000))

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

            # Build debug regions with geometry
            debug_regions: list[DebugTextRegion] = []
            for i, region in enumerate(classified_regions):
                # Find translation if available
                translated = next(
                    (tr for tr in translated_regions if tr.original_text == region.text),
                    None,
                )

                # Extract geometry if available (stored in _geometry attribute from OCR)
                geometry = None
                if hasattr(region, "_geometry"):
                    geometry = region._geometry

                # Convert boundingBox [x1, y1, x2, y2] to bbox_norm [x, y, width, height]
                bbox = region.boundingBox
                if len(bbox) >= 4:
                    x, y = bbox[0], bbox[1]
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    bbox_norm = [x, y, width, height]
                else:
                    bbox_norm = [0.0, 0.0, 0.0, 0.0]

                debug_regions.append(
                    DebugTextRegion(
                        id=f"region_{i}",
                        role=region.role,
                        bbox_norm=bbox_norm,
                        original_text=region.text,
                        translated_text=translated.translated_text if translated else None,
                        is_localizable=self._is_localizable(region),
                        geometry=geometry,
                    )
                )

            logger.info(
                f"PipelineStageEnd job={job.jobId} stage={stage_name} "
                f"durationMs={packaging_time_ms} skipped={skipped}"
            )
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
                debug=DebugInfo(
                    regions=debug_regions,
                    timings=ProcessingTimeMs(
                        ocr=ocr_time_ms,
                        translation=translation_time_ms,
                        inpaint=inpaint_time_ms,
                        packaging=packaging_time_ms,
                        total=total_time_ms,
                    ),
                ),
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

    def _get_image_for_step(
        self, job_id: str, step: str, original_bytes: bytes, target_long_side_px: int
    ) -> bytes:
        """
        Get image bytes for a pipeline step, generating derivative if needed.

        Args:
            job_id: Job identifier
            step: Pipeline step name (OCR, TRANSLATION, INPAINT)
            original_bytes: Original image bytes
            target_long_side_px: Target long side in pixels

        Returns:
            Image bytes (derivative if needed, or original)
        """
        # Check cache first
        cache_key = (job_id, step, target_long_side_px)
        if cache_key in self._derivative_cache:
            return self._derivative_cache[cache_key]

        # Get original dimensions
        try:
            orig_width, orig_height = get_image_dimensions(original_bytes)
            orig_long_side = max(orig_width, orig_height)
        except Exception as e:
            logger.warning(f"Failed to get image dimensions for job {job_id}, using original: {e}")
            return original_bytes

        # Check if derivative is needed
        if orig_long_side <= target_long_side_px:
            # No derivative needed
            logger.info(
                f"ImageDerivativeNotNeeded job={job_id} step={step} dims={orig_width}x{orig_height}"
            )
            self._derivative_cache[cache_key] = original_bytes
            return original_bytes

        # Generate derivative
        try:
            derivative_bytes = maybe_make_derivative(
                original_bytes, target_long_side_px, format="JPEG", quality=90
            )
            deriv_width, deriv_height = get_image_dimensions(derivative_bytes)
            logger.info(
                f"ImageDerivativeGenerated job={job_id} step={step} "
                f"from={orig_width}x{orig_height} to={deriv_width}x{deriv_height} "
                f"long_side_px={target_long_side_px} size_bytes={len(derivative_bytes)}"
            )
            self._derivative_cache[cache_key] = derivative_bytes
            return derivative_bytes
        except Exception as e:
            logger.warning(f"Failed to generate derivative for job {job_id} step {step}, using original: {e}")
            self._derivative_cache[cache_key] = original_bytes
            return original_bytes

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
