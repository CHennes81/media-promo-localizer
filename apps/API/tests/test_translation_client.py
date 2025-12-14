"""
Tests for translation client implementations.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.interfaces import TranslatedRegion
from app.clients.translation_client import LlmTranslationClient
from app.models.jobs import DetectedText


@pytest.fixture
def sample_regions():
    """Sample text regions for testing."""
    return [
        DetectedText(text="THE GREAT HEIST", boundingBox=[0.1, 0.2, 0.8, 0.28], role="title"),
        DetectedText(text="COMING SOON", boundingBox=[0.12, 0.9, 0.78, 0.95], role="tagline"),
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    {
                        "translations": [
                            {"originalText": "THE GREAT HEIST", "translatedText": "LE GRAND CASSE"},
                            {"originalText": "COMING SOON", "translatedText": "BIENTÔT"},
                        ]
                    }
                )
            )
        )
    ]
    return response


@pytest.mark.asyncio
async def test_llm_translation_client_success(sample_regions, mock_openai_response):
    """Test successful translation."""
    with patch("app.clients.translation_client.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_openai.return_value = mock_client

        client = LlmTranslationClient(api_key="test-key")
        result = await client.translate_text_regions(sample_regions, "fr-FR")

        assert len(result) == 2
        assert all(isinstance(r, TranslatedRegion) for r in result)
        assert result[0].translated_text == "LE GRAND CASSE"
        assert result[1].translated_text == "BIENTÔT"


@pytest.mark.asyncio
async def test_llm_translation_client_api_error(sample_regions):
    """Test translation client handles API errors."""
    with patch("app.clients.translation_client.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_openai.return_value = mock_client

        client = LlmTranslationClient(api_key="test-key")
        with pytest.raises(Exception) as exc_info:
            await client.translate_text_regions(sample_regions, "fr-FR")

        assert "Translation processing failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_llm_translation_client_invalid_json(sample_regions):
    """Test translation client handles invalid JSON response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="not json"))]

    with patch("app.clients.translation_client.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = LlmTranslationClient(api_key="test-key")
        with pytest.raises(Exception) as exc_info:
            await client.translate_text_regions(sample_regions, "fr-FR")

        assert "Invalid response format" in str(exc_info.value)


def test_llm_translation_client_missing_api_key():
    """Test translation client requires API key."""
    with pytest.raises(ValueError) as exc_info:
        LlmTranslationClient(api_key="")
    assert "OPENAI_API_KEY is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_llm_translation_client_no_nameerror_on_exception(sample_regions):
    """Test that translation client doesn't raise NameError/UnboundLocalError on exceptions.

    This test ensures correlation_str and content are always defined before use in except blocks.
    """
    with patch("app.clients.translation_client.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        # Simulate an exception during API call
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Network error"))
        mock_openai.return_value = mock_client

        client = LlmTranslationClient(api_key="test-key", model="gpt-4o-mini")

        # Should raise Exception but NOT NameError or UnboundLocalError
        with pytest.raises(Exception) as exc_info:
            await client.translate_text_regions(sample_regions, "fr-FR", job_id="test_job_123")

        # Verify it's our wrapped exception, not a NameError
        assert "Translation processing failed" in str(exc_info.value)
        assert not isinstance(exc_info.value, NameError)
        assert not isinstance(exc_info.value, UnboundLocalError)


@pytest.mark.asyncio
async def test_llm_translation_client_logs_service_response_on_success(sample_regions, mock_openai_response, caplog):
    """Test that translation client logs ServiceResponse on success."""
    with patch("app.clients.translation_client.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_openai.return_value = mock_client

        client = LlmTranslationClient(api_key="test-key")
        await client.translate_text_regions(sample_regions, "fr-FR", job_id="test_job_123")

        # Verify ServiceResponse log was emitted
        log_messages = [record.message for record in caplog.records]
        service_response_logs = [msg for msg in log_messages if "ServiceResponse" in msg and "TRANSLATION" in msg]
        assert len(service_response_logs) > 0
        assert any("status=200" in msg for msg in service_response_logs)
        assert any("durationMs=" in msg for msg in service_response_logs)
        assert any("responseSizeBytes=" in msg for msg in service_response_logs)
