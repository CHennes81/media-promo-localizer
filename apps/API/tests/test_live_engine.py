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
from app.models import DetectedText, JobStatus, LocalizationJob
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

