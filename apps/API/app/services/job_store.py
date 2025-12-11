"""
In-memory job store for localization jobs.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.models import JobStatus, LocalizationJob

logger = logging.getLogger("media_promo_localizer")


class JobStore:
    """In-memory job store with eviction support."""

    def __init__(self, max_jobs: int = None, ttl_seconds: int = None):
        """
        Initialize job store.

        Args:
            max_jobs: Maximum number of jobs to store (default from config)
            ttl_seconds: Time-to-live for jobs in seconds (default from config)
        """
        self._jobs: dict[str, LocalizationJob] = {}
        self._max_jobs = max_jobs or settings.MAX_JOBS
        self._ttl_seconds = ttl_seconds or settings.JOB_TTL_SECONDS

    def create_job(
        self,
        job_id: str,
        target_language: str,
        source_language: Optional[str] = None,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        job_metadata: Optional[dict] = None,
    ) -> LocalizationJob:
        """
        Create a new job.

        Args:
            job_id: Unique job identifier
            target_language: Target language code (BCP-47)
            source_language: Source language code (optional)
            file_path: Path to uploaded file
            file_name: Original filename
            file_size: File size in bytes
            job_metadata: Optional metadata dict

        Returns:
            Created LocalizationJob

        Raises:
            ValueError: If max jobs limit is exceeded
        """
        # Evict old jobs if we're at capacity
        if len(self._jobs) >= self._max_jobs:
            self._evict_old_jobs()

        # If still at capacity, reject
        if len(self._jobs) >= self._max_jobs:
            raise ValueError(
                f"Job store is at capacity ({self._max_jobs} jobs). "
                "Please wait for jobs to complete or expire."
            )

        now = datetime.now(timezone.utc)
        job = LocalizationJob(
            jobId=job_id,
            status=JobStatus.QUEUED,
            createdAt=now,
            updatedAt=now,
            targetLanguage=target_language,
            sourceLanguage=source_language,
            filePath=file_path,
            fileName=file_name,
            fileSize=file_size,
            jobMetadata=job_metadata,
        )

        self._jobs[job_id] = job
        logger.info(f"JobCreated jobId={job_id} targetLang={target_language}")
        return job

    def get_job(self, job_id: str) -> Optional[LocalizationJob]:
        """
        Get a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            LocalizationJob if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if job:
            # Check if job has expired
            age_seconds = (datetime.now(timezone.utc) - job.createdAt).total_seconds()
            if age_seconds > self._ttl_seconds:
                logger.debug(f"Job {job_id} has expired (age: {age_seconds}s)")
                del self._jobs[job_id]
                return None
        return job

    def update_job(self, job: LocalizationJob) -> None:
        """
        Update an existing job.

        Args:
            job: Updated LocalizationJob
        """
        if job.jobId not in self._jobs:
            raise ValueError(f"Job {job.jobId} not found in store")

        job.updatedAt = datetime.now(timezone.utc)
        self._jobs[job.jobId] = job
        logger.debug(f"JobUpdated jobId={job.jobId} status={job.status}")

    def _evict_old_jobs(self) -> None:
        """Evict jobs that have exceeded TTL."""
        now = datetime.now(timezone.utc)
        expired_jobs = [
            job_id
            for job_id, job in self._jobs.items()
            if (now - job.createdAt).total_seconds() > self._ttl_seconds
        ]

        for job_id in expired_jobs:
            del self._jobs[job_id]
            logger.debug(f"Evicted expired job {job_id}")

        # If still at capacity, evict oldest jobs
        if len(self._jobs) >= self._max_jobs:
            sorted_jobs = sorted(
                self._jobs.items(), key=lambda x: x[1].createdAt
            )
            num_to_evict = len(self._jobs) - self._max_jobs + 1
            for job_id, _ in sorted_jobs[:num_to_evict]:
                del self._jobs[job_id]
                logger.debug(f"Evicted oldest job {job_id} to make room")


# Global singleton instance
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """Get the global job store instance."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store


