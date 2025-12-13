"""
Tests for OCR client implementations.
"""
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.interfaces import OcrResult
from app.clients.ocr_client import CloudOcrClient
from app.models import DetectedText


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response for OCR API."""
    response = MagicMock()
    response.json.return_value = {
        "responses": [
            {
                "textAnnotations": [
                    {
                        "description": "THE GREAT HEIST\nCOMING SOON",
                        "boundingPoly": {
                            "vertices": [
                                {"x": 0, "y": 0},
                                {"x": 100, "y": 0},
                                {"x": 100, "y": 50},
                                {"x": 0, "y": 50},
                            ]
                        },
                    },
                    {
                        "description": "THE GREAT HEIST",
                        "boundingPoly": {
                            "vertices": [
                                {"x": 10, "y": 10},
                                {"x": 90, "y": 10},
                                {"x": 90, "y": 30},
                                {"x": 10, "y": 30},
                            ]
                        },
                    },
                    {
                        "description": "COMING SOON",
                        "boundingPoly": {
                            "vertices": [
                                {"x": 10, "y": 40},
                                {"x": 80, "y": 40},
                                {"x": 80, "y": 50},
                                {"x": 10, "y": 50},
                            ]
                        },
                    },
                ]
            }
        ]
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def sample_image_bytes():
    """Sample image bytes for testing."""
    # Create a minimal valid JPEG header
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9"


@pytest.mark.asyncio
async def test_cloud_ocr_client_success(mock_httpx_response, sample_image_bytes):
    """Test successful OCR recognition."""
    with patch("app.clients.ocr_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )
        with patch("app.clients.ocr_client.Image.open") as mock_image:
            mock_img = MagicMock()
            mock_img.size = (100, 50)
            mock_image.return_value = mock_img

            client = CloudOcrClient(api_key="test-key")
            result = await client.recognize_text(sample_image_bytes)

            assert isinstance(result, OcrResult)
            assert result.image_width == 100
            assert result.image_height == 50
            assert len(result.text_regions) == 2  # Excluding full text annotation
            assert all(isinstance(r, DetectedText) for r in result.text_regions)


@pytest.mark.asyncio
async def test_cloud_ocr_client_api_error(sample_image_bytes):
    """Test OCR client handles API errors."""
    import httpx

    with patch("app.clients.ocr_client.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

        mock_client.return_value.__aenter__.return_value.post = mock_post
        with patch("app.clients.ocr_client.Image.open") as mock_image:
            mock_img = MagicMock()
            mock_img.size = (100, 50)
            mock_image.return_value = mock_img

            client = CloudOcrClient(api_key="test-key")
            with pytest.raises(Exception) as exc_info:
                await client.recognize_text(sample_image_bytes)

            assert "OCR service returned error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cloud_ocr_client_timeout(sample_image_bytes):
    """Test OCR client handles timeout errors."""
    import httpx

    with patch("app.clients.ocr_client.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        mock_client.return_value.__aenter__.return_value.post = mock_post
        with patch("app.clients.ocr_client.Image.open") as mock_image:
            mock_img = MagicMock()
            mock_img.size = (100, 50)
            mock_image.return_value = mock_img

            client = CloudOcrClient(api_key="test-key")
            with pytest.raises(Exception) as exc_info:
                await client.recognize_text(sample_image_bytes)

            assert "OCR service timeout" in str(exc_info.value)


def test_cloud_ocr_client_missing_api_key():
    """Test OCR client requires API key."""
    with pytest.raises(ValueError) as exc_info:
        CloudOcrClient(api_key="")
    assert "OCR_API_KEY is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cloud_ocr_client_logs_job_id(mock_httpx_response, sample_image_bytes):
    """Test that OCR client includes job_id in ServiceCall logs when provided."""
    with patch("app.clients.ocr_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_httpx_response
        )
        with patch("app.clients.ocr_client.Image.open") as mock_image:
            mock_img = MagicMock()
            mock_img.size = (100, 50)
            mock_image.return_value = mock_img

            # Capture log messages
            log_messages = []
            handler = logging.Handler()
            handler.emit = lambda record: log_messages.append(record.getMessage())
            logger = logging.getLogger("media_promo_localizer")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            try:
                client = CloudOcrClient(api_key="test-key")
                test_job_id = "test-job-123"
                await client.recognize_text(sample_image_bytes, job_id=test_job_id)

                # Verify ServiceCall log contains job_id
                service_call_logs = [
                    msg for msg in log_messages if "ServiceCall" in msg and "OCR" in msg
                ]
                assert len(service_call_logs) > 0, "ServiceCall log should be emitted"
                assert f"job={test_job_id}" in service_call_logs[0], (
                    f"ServiceCall log should contain job={test_job_id}, "
                    f"got: {service_call_logs[0]}"
                )

                # Verify ServiceResponse log also contains job_id
                service_response_logs = [
                    msg
                    for msg in log_messages
                    if "ServiceResponse" in msg and "OCR" in msg
                ]
                assert len(service_response_logs) > 0, "ServiceResponse log should be emitted"
                assert f"job={test_job_id}" in service_response_logs[0], (
                    f"ServiceResponse log should contain job={test_job_id}, "
                    f"got: {service_response_logs[0]}"
                )
            finally:
                logger.removeHandler(handler)
