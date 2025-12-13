"""
Mock localization engine for Sprint 2.
Simulates the OCR → translation → inpainting → packaging pipeline.
"""
import asyncio
import logging
import random
import time
from datetime import datetime, timezone

from app.config import settings
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


async def run(job: LocalizationJob) -> LocalizationJob:
    """
    Run the mock localization pipeline.

    Args:
        job: LocalizationJob to process

    Returns:
        Updated LocalizationJob with result or error
    """
    try:
        job.status = JobStatus.PROCESSING
        job.updatedAt = datetime.now(timezone.utc)

        # Stage 1: OCR
        stage_name = "OCR"
        logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
        ocr_start = time.perf_counter()
        skipped = False

        if settings.SKIP_OCR:
            skipped = True
            logger.info(
                f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                f"reason=env_var env=SKIP_OCR value=true"
            )
            ocr_time_ms = max(1, int((time.perf_counter() - ocr_start) * 1000))
        else:
            ocr_time_ms = await _simulate_stage("ocr", 800, 2000)

        job.progress = Progress(
            stage=ProgressStage.OCR,
            percent=25,
            stageTimingsMs={"ocr": ocr_time_ms},
        )
        job.updatedAt = datetime.now(timezone.utc)
        logger.info(
            f"PipelineStageEnd job={job.jobId} stage={stage_name} "
            f"durationMs={ocr_time_ms} skipped={skipped}"
        )

        # Stage 2: Translation
        stage_name = "TRANSLATION"
        logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
        translation_start = time.perf_counter()
        skipped = False

        if settings.SKIP_TRANSLATION:
            skipped = True
            logger.info(
                f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                f"reason=env_var env=SKIP_TRANSLATION value=true"
            )
            translation_time_ms = max(1, int((time.perf_counter() - translation_start) * 1000))
        else:
            translation_time_ms = await _simulate_stage("translation", 600, 1500)

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
            f"durationMs={translation_time_ms} skipped={skipped}"
        )

        # Stage 3: Inpainting
        stage_name = "INPAINT"
        logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
        inpaint_start = time.perf_counter()
        skipped = False

        if settings.SKIP_INPAINT:
            skipped = True
            logger.info(
                f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                f"reason=env_var env=SKIP_INPAINT value=true"
            )
            inpaint_time_ms = max(1, int((time.perf_counter() - inpaint_start) * 1000))
        else:
            inpaint_time_ms = await _simulate_stage("inpaint", 3000, 6000)

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

        # Stage 4: Packaging
        stage_name = "PACKAGING"
        logger.info(f"PipelineStageStart job={job.jobId} stage={stage_name}")
        packaging_start = time.perf_counter()
        skipped = False

        if settings.SKIP_PACKAGING:
            skipped = True
            logger.info(
                f"PipelineStageSkipped job={job.jobId} stage={stage_name} "
                f"reason=env_var env=SKIP_PACKAGING value=true"
            )
            packaging_time_ms = max(1, int((time.perf_counter() - packaging_start) * 1000))
        else:
            packaging_time_ms = await _simulate_stage("packaging", 200, 500)

        total_time_ms = ocr_time_ms + translation_time_ms + inpaint_time_ms + packaging_time_ms
        logger.info(
            f"PipelineStageEnd job={job.jobId} stage={stage_name} "
            f"durationMs={packaging_time_ms} skipped={skipped}"
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

        # Generate mock result
        job.result = _generate_mock_result(
            job.jobId,
            job.targetLanguage,
            job.sourceLanguage or "en-US",
            ProcessingTimeMs(
                ocr=ocr_time_ms,
                translation=translation_time_ms,
                inpaint=inpaint_time_ms,
                total=total_time_ms,
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


async def _simulate_stage(stage_name: str, min_ms: int, max_ms: int) -> int:
    """
    Simulate a processing stage with random delay.

    Args:
        stage_name: Name of the stage (for logging)
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds

    Returns:
        Actual delay in milliseconds
    """
    delay_ms = random.randint(min_ms, max_ms)
    await asyncio.sleep(delay_ms / 1000.0)
    return delay_ms


def _generate_mock_result(
    job_id: str,
    target_language: str,
    source_language: str,
    processing_time_ms: ProcessingTimeMs,
) -> JobResult:
    """
    Generate a mock result for a completed job.

    Args:
        job_id: Job identifier
        target_language: Target language code
        source_language: Source language code
        processing_time_ms: Processing time breakdown

    Returns:
        JobResult with mock data
    """
    # Generate mock image URLs (placeholder paths)
    image_url = f"/static/jobs/{job_id}/output.png"
    thumbnail_url = f"/static/jobs/{job_id}/thumb.png"

    # Generate mock detected text with normalized bounding boxes
    detected_text = [
        DetectedText(
            text="THE GREAT HEIST",
            boundingBox=[0.10, 0.20, 0.80, 0.28],  # Normalized [x1, y1, x2, y2]
            role="title",
        ),
        DetectedText(
            text="COMING SOON",
            boundingBox=[0.12, 0.90, 0.78, 0.95],
            role="tagline",
        ),
        DetectedText(
            text="Directed by John Smith",
            boundingBox=[0.15, 0.85, 0.75, 0.88],
            role="credits",
        ),
        DetectedText(
            text="[FPO - Manual Art Required]",
            boundingBox=[0.05, 0.30, 0.95, 0.50],
            role="other",  # Marked as tricky/FPO for demo
        ),
    ]

    return JobResult(
        imageUrl=image_url,
        thumbnailUrl=thumbnail_url,
        processingTimeMs=processing_time_ms,
        language=target_language,
        sourceLanguage=source_language,
        detectedText=detected_text,
    )
