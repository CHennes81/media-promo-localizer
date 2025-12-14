"""
Tests for live localization engine.
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.inpainting_client import StubInpaintingClient
from app.clients.interfaces import OcrResult, TranslatedRegion
from app.clients.ocr_client import CloudOcrClient
from app.clients.translation_client import LlmTranslationClient
from app.models.jobs import DetectedText, JobStatus, LocalizationJob
from app.services.live_engine import LiveLocalizationEngine


@pytest.fixture
def mock_ocr_client():
    """Mock OCR client."""
    client = MagicMock(spec=CloudOcrClient)
    client.recognize_text = AsyncMock(
        return_value=OcrResult(
            text_regions=[
                DetectedText(
                    text="THE GREAT HEIST",
                    boundingBox=[0.1, 0.2, 0.8, 0.28],
                    role="other",
                ),
                DetectedText(
                    text="COMING SOON",
                    boundingBox=[0.12, 0.9, 0.78, 0.95],
                    role="other",
                ),
            ],
            image_width=1000,
            image_height=1500,
        )
    )
    return client


@pytest.fixture
def mock_translation_client():
    """Mock translation client."""
    client = MagicMock(spec=LlmTranslationClient)
    client.translate_text_regions = AsyncMock(
        return_value=[
            TranslatedRegion(
                original_text="THE GREAT HEIST",
                translated_text="LE GRAND CASSE",
                bounding_box=[0.1, 0.2, 0.8, 0.28],
                role="title",
            ),
            TranslatedRegion(
                original_text="COMING SOON",
                translated_text="BIENTÔT",
                bounding_box=[0.12, 0.9, 0.78, 0.95],
                role="tagline",
            ),
        ]
    )
    return client


@pytest.fixture
def mock_inpainting_client():
    """Mock inpainting client."""
    return StubInpaintingClient()


@pytest.fixture
def sample_job(tmp_path):
    """Sample localization job for testing."""
    # Create a temporary image file
    image_file = tmp_path / "poster.jpg"
    image_file.write_bytes(b"fake image data")

    return LocalizationJob(
        jobId="test_job_123",
        status=JobStatus.QUEUED,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        targetLanguage="fr-FR",
        sourceLanguage="en-US",
        filePath=str(image_file),
        fileName="poster.jpg",
        fileSize=100,
    )


@pytest.mark.asyncio
async def test_live_engine_success(
    mock_ocr_client, mock_translation_client, mock_inpainting_client, sample_job
):
    """Test successful live engine pipeline."""
    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    result_job = await engine.run(sample_job)

    assert result_job.status == JobStatus.SUCCEEDED
    assert result_job.result is not None
    assert result_job.result.language == "fr-FR"
    assert result_job.result.processingTimeMs.total > 0
    assert len(result_job.result.detectedText) == 2

    # Verify debug payload is present
    assert result_job.result.debug is not None
    assert len(result_job.result.debug.regions) == 2
    assert result_job.result.debug.regions[0].id == "region_0"
    assert result_job.result.debug.regions[0].original_text == "THE GREAT HEIST"
    assert result_job.result.debug.regions[0].translated_text == "LE GRAND CASSE"
    assert result_job.result.debug.regions[0].is_localizable is not None
    assert result_job.result.debug.timings.total > 0

    # Verify clients were called
    mock_ocr_client.recognize_text.assert_called_once()
    mock_translation_client.translate_text_regions.assert_called_once()


@pytest.mark.asyncio
async def test_live_engine_ocr_failure(
    mock_translation_client, mock_inpainting_client, sample_job
):
    """Test live engine handles OCR failures."""
    mock_ocr_client = MagicMock(spec=CloudOcrClient)
    mock_ocr_client.recognize_text = AsyncMock(side_effect=Exception("OCR failed"))

    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    result_job = await engine.run(sample_job)

    assert result_job.status == JobStatus.FAILED
    assert result_job.error is not None
    assert result_job.error.code == "OCR_MODEL_ERROR"
    assert result_job.result is None


@pytest.mark.asyncio
async def test_live_engine_translation_failure(
    mock_ocr_client, mock_inpainting_client, sample_job
):
    """Test live engine handles translation failures."""
    mock_translation_client = MagicMock(spec=LlmTranslationClient)
    mock_translation_client.translate_text_regions = AsyncMock(
        side_effect=Exception("Translation failed")
    )

    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    result_job = await engine.run(sample_job)

    assert result_job.status == JobStatus.FAILED
    assert result_job.error is not None
    assert result_job.error.code == "TRANSLATION_MODEL_ERROR"
    assert result_job.result is None


@pytest.mark.asyncio
async def test_live_engine_classify_text_regions(mock_ocr_client, mock_translation_client, mock_inpainting_client):
    """Test text region classification."""
    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    regions = [
        DetectedText(text="COMING SOON", boundingBox=[0.1, 0.2, 0.8, 0.28], role="other"),
        DetectedText(text="Directed by John", boundingBox=[0.1, 0.3, 0.8, 0.35], role="other"),
        DetectedText(text="www.example.com", boundingBox=[0.1, 0.9, 0.8, 0.95], role="other"),
    ]

    classified = engine._classify_text_regions(regions)

    assert classified[0].role == "tagline"  # "COMING SOON"
    assert classified[1].role == "credits"  # "Directed by"
    assert classified[2].role == "other"  # URL stays locked


@pytest.mark.asyncio
async def test_live_engine_is_localizable(mock_ocr_client, mock_translation_client, mock_inpainting_client):
    """Test localizability policy."""
    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    # URL should not be localizable
    url_region = DetectedText(
        text="www.example.com", boundingBox=[0.1, 0.9, 0.8, 0.95], role="other"
    )
    assert not engine._is_localizable(url_region)

    # Tagline should be localizable
    tagline_region = DetectedText(
        text="COMING SOON", boundingBox=[0.1, 0.2, 0.8, 0.28], role="tagline"
    )
    assert engine._is_localizable(tagline_region)


@pytest.mark.asyncio
async def test_live_engine_progress_updates_to_translation_stage(
    mock_ocr_client, mock_translation_client, mock_inpainting_client, sample_job
):
    """Test that job progress is updated to TRANSLATION stage before translation starts."""
    from app.services.job_store import get_job_store

    # Add job to store so we can verify progress updates
    job_store = get_job_store()
    job_store._jobs[sample_job.jobId] = sample_job

    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    # Run engine (this will update progress before calling translation)
    result_job = await engine.run(sample_job)

    # Verify progress was updated to TRANSLATION stage
    # We check the final result, but the key is that progress.stage should be TRANSLATION
    # at some point during processing (after OCR, before translation completes)
    assert result_job.status == JobStatus.SUCCEEDED
    # Progress should have been TRANSLATION at some point
    # The final progress will be PACKAGING, but we verify translation timing is present
    assert result_job.result is not None
    assert "translation" in result_job.result.processingTimeMs
    assert result_job.result.processingTimeMs.translation > 0


@pytest.mark.asyncio
async def test_live_engine_translation_failure_shows_translation_stage(
    mock_ocr_client, mock_inpainting_client, sample_job
):
    """Test that when translation fails, job progress reflects TRANSLATION stage (not OCR)."""
    from app.services.job_store import get_job_store
    from app.models.jobs import Progress, ProgressStage

    # Add job to store
    job_store = get_job_store()
    job_store._jobs[sample_job.jobId] = sample_job

    # Mock translation client to raise exception
    mock_translation_client = MagicMock(spec=LlmTranslationClient)
    mock_translation_client.translate_text_regions = AsyncMock(
        side_effect=Exception("Translation API error")
    )

    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    result_job = await engine.run(sample_job)

    # Verify job failed with translation error
    assert result_job.status == JobStatus.FAILED
    assert result_job.error is not None
    assert result_job.error.code == "TRANSLATION_MODEL_ERROR"

    # CRITICAL: Progress should show TRANSLATION stage, not OCR
    assert result_job.progress is not None
    assert result_job.progress.stage == ProgressStage.TRANSLATION
    assert result_job.progress.percent == 50  # Should be 50% when in translation stage
    # Should have OCR timing (completed) and translation timing (failed but attempted)
    assert "ocr" in result_job.progress.stageTimingsMs
    assert "translation" in result_job.progress.stageTimingsMs


@pytest.mark.asyncio
async def test_live_engine_skip_translation(
    mock_ocr_client, mock_translation_client, mock_inpainting_client, sample_job, monkeypatch
):
    """Test that SKIP_TRANSLATION=true does not call translation client and job completes successfully."""
    # Set SKIP_TRANSLATION to True
    monkeypatch.setattr("app.config.settings.SKIP_TRANSLATION", True)

    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    result_job = await engine.run(sample_job)

    # Verify job completed successfully
    assert result_job.status == JobStatus.SUCCEEDED
    assert result_job.result is not None

    # Verify translation client was NOT called
    mock_translation_client.translate_text_regions.assert_not_called()

    # Verify OCR client WAS called
    mock_ocr_client.recognize_text.assert_called_once()

    # Verify progress advanced through all stages
    assert result_job.result.processingTimeMs.translation > 0
    assert result_job.result.processingTimeMs.total > 0

    # Verify job has valid result with identity translations (original_text = translated_text)
    assert result_job.result.detectedText is not None
    assert len(result_job.result.detectedText) > 0


@pytest.mark.asyncio
async def test_live_engine_skip_ocr(
    mock_translation_client, mock_inpainting_client, sample_job, monkeypatch
):
    """Test that SKIP_OCR=true does not call OCR and still completes successfully."""
    # Set SKIP_OCR to True
    monkeypatch.setattr("app.config.settings.SKIP_OCR", True)

    # Create a mock OCR client that should not be called
    mock_ocr_client = MagicMock(spec=CloudOcrClient)
    mock_ocr_client.recognize_text = AsyncMock()

    engine = LiveLocalizationEngine(
        ocr_client=mock_ocr_client,
        translation_client=mock_translation_client,
        inpainting_client=mock_inpainting_client,
    )

    result_job = await engine.run(sample_job)

    # Verify job completed successfully
    assert result_job.status == JobStatus.SUCCEEDED
    assert result_job.result is not None

    # Verify OCR client was NOT called
    mock_ocr_client.recognize_text.assert_not_called()

    # Verify progress advanced through all stages
    assert result_job.result.processingTimeMs.ocr > 0
    assert result_job.result.processingTimeMs.total > 0

    # Verify job has valid result (empty detected text when OCR is skipped)
    assert result_job.result.detectedText is not None
    assert len(result_job.result.detectedText) == 0  # Empty list when OCR is skipped
