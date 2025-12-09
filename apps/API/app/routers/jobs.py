"""
Localization job endpoints.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import CreateJobResponse, JobStatus, LocalizationJob
from app.services.job_store import get_job_store
from app.services.mock_engine import run as run_mock_engine
from app.utils.errors import APIError, ErrorCodes, create_error_response, handle_exception

logger = logging.getLogger("media_promo_localizer")

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path("apps/api/tmp/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"loc_{uuid.uuid4().hex[:26].upper()}"


def _validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file.

    Args:
        file: Uploaded file

    Raises:
        APIError: If file is invalid
    """
    if not file.filename:
        raise APIError(
            code=ErrorCodes.INVALID_INPUT,
            message="File is required.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    # Check MIME type
    content_type = file.content_type
    if content_type not in settings.ALLOWED_MIME_TYPES:
        raise APIError(
            code=ErrorCodes.UNSUPPORTED_MEDIA_TYPE,
            message=f"Unsupported file type. Allowed types: {', '.join(settings.ALLOWED_MIME_TYPES)}",
            http_status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


async def _save_uploaded_file(file: UploadFile, job_id: str) -> tuple[str, int]:
    """
    Save uploaded file to disk.

    Args:
        file: Uploaded file
        job_id: Job identifier

    Returns:
        Tuple of (file_path, file_size)

    Raises:
        APIError: If file is too large or save fails
    """
    # Determine file extension from content type
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png"}
    ext = ext_map.get(file.content_type, ".jpg")

    # Create job-specific directory
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    file_path = job_dir / f"poster{ext}"
    file_size = 0

    try:
        # Read file in chunks to check size
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
                    file_path.unlink(missing_ok=True)
                    raise APIError(
                        code=ErrorCodes.PAYLOAD_TOO_LARGE,
                        message=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_MB} MB.",
                        http_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    )
                f.write(chunk)

        return str(file_path), file_size
    except APIError:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        logger.error(f"Failed to save uploaded file: {e}", exc_info=True)
        raise APIError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="Failed to save uploaded file.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def _process_job_background(job: LocalizationJob) -> None:
    """
    Background task to process a localization job.

    Args:
        job: LocalizationJob to process
    """
    try:
        job_store = get_job_store()
        # Update status to processing
        job.status = JobStatus.PROCESSING
        job.updatedAt = datetime.now(timezone.utc)
        job_store.update_job(job)

        # Run mock engine
        updated_job = await run_mock_engine(job)

        # Update job store with final result
        job_store.update_job(updated_job)
    except Exception as e:
        logger.error(f"Background processing failed for job {job.jobId}: {e}", exc_info=True)
        job_store = get_job_store()
        job.status = JobStatus.FAILED
        job.updatedAt = datetime.now(timezone.utc)
        from app.models import ErrorInfo

        job.error = ErrorInfo(
            code=ErrorCodes.INTERNAL_ERROR,
            message="An error occurred during background processing.",
            retryable=True,
        )
        job_store.update_job(job)


@router.post("/localization-jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_localization_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    targetLanguage: str = Form(...),
    sourceLanguage: Optional[str] = Form(None),
    jobMetadata: Optional[str] = Form(None),
):
    """
    Create a new localization job.

    Args:
        background_tasks: FastAPI background tasks
        file: Poster image file
        targetLanguage: Target language code (BCP-47)
        sourceLanguage: Source language code (optional)
        jobMetadata: Optional JSON metadata string

    Returns:
        CreateJobResponse with job ID and status
    """
    try:
        # Validate inputs
        if not targetLanguage:
            raise APIError(
                code=ErrorCodes.INVALID_INPUT,
                message="targetLanguage is required.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        _validate_file(file)

        # Parse job metadata if provided
        metadata_dict = None
        if jobMetadata:
            try:
                import json

                metadata_dict = json.loads(jobMetadata)
            except json.JSONDecodeError:
                raise APIError(
                    code=ErrorCodes.INVALID_INPUT,
                    message="jobMetadata must be valid JSON.",
                    http_status=status.HTTP_400_BAD_REQUEST,
                )

        # Generate job ID
        job_id = _generate_job_id()

        # Save uploaded file
        file_path, file_size = await _save_uploaded_file(file, job_id)

        # Create job in store
        job_store = get_job_store()
        try:
            job = job_store.create_job(
                job_id=job_id,
                target_language=targetLanguage,
                source_language=sourceLanguage,
                file_path=file_path,
                file_name=file.filename,
                file_size=file_size,
                job_metadata=metadata_dict,
            )
        except ValueError as e:
            # Job store at capacity
            # Clean up uploaded file
            Path(file_path).unlink(missing_ok=True)
            raise APIError(
                code=ErrorCodes.INTERNAL_ERROR,
                message=str(e),
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Schedule background processing
        background_tasks.add_task(_process_job_background, job)

        # Return 202 Accepted
        return CreateJobResponse(
            jobId=job.jobId,
            status=job.status,
            createdAt=job.createdAt,
            estimatedSeconds=8,  # Mock estimate
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating job: {e}", exc_info=True)
        raise APIError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="An unexpected error occurred while creating the job.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/localization-jobs/{job_id}")
async def get_localization_job(job_id: str):
    """
    Get localization job status and result.

    Args:
        job_id: Job identifier

    Returns:
        GetJobResponse with job status and result
    """
    try:
        job_store = get_job_store()
        job = job_store.get_job(job_id)

        if not job:
            raise APIError(
                code=ErrorCodes.NOT_FOUND,
                message="Localization job not found.",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        return job.to_get_response()

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting job {job_id}: {e}", exc_info=True)
        raise APIError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="An unexpected error occurred while retrieving the job.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
