"""
Tests for mock localization engine skip behavior.
"""
import pytest
from datetime import datetime, timezone

from app.models import JobStatus, LocalizationJob
from app.services import mock_engine


@pytest.fixture
def sample_job():
    """Sample localization job for testing."""
    return LocalizationJob(
        jobId="test_job_123",
        status=JobStatus.QUEUED,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        targetLanguage="fr-FR",
        sourceLanguage="en-US",
    )


@pytest.mark.asyncio
async def test_mock_engine_skip_translation(sample_job, monkeypatch):
    """Test that SKIP_TRANSLATION=true does not call translation and job completes successfully."""
    # Set SKIP_TRANSLATION to True
    monkeypatch.setattr("app.config.settings.SKIP_TRANSLATION", True)

    result_job = await mock_engine.run(sample_job)

    # Verify job completed successfully
    assert result_job.status == JobStatus.SUCCEEDED
    assert result_job.result is not None

    # Verify progress advanced through all stages
    assert result_job.result.processingTimeMs.translation > 0
    assert result_job.result.processingTimeMs.total > 0

    # Verify job has valid result
    assert result_job.result.detectedText is not None
    assert len(result_job.result.detectedText) > 0


@pytest.mark.asyncio
async def test_mock_engine_skip_ocr(sample_job, monkeypatch):
    """Test that SKIP_OCR=true does not call OCR and still completes successfully."""
    # Set SKIP_OCR to True
    monkeypatch.setattr("app.config.settings.SKIP_OCR", True)

    result_job = await mock_engine.run(sample_job)

    # Verify job completed successfully
    assert result_job.status == JobStatus.SUCCEEDED
    assert result_job.result is not None

    # Verify progress advanced through all stages
    assert result_job.result.processingTimeMs.ocr > 0
    assert result_job.result.processingTimeMs.total > 0

    # Verify job has valid result
    assert result_job.result.detectedText is not None
    assert len(result_job.result.detectedText) > 0
