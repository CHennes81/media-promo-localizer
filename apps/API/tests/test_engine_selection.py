"""
Tests for localization engine selection based on LOCALIZATION_MODE.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.config import settings
from app.routers.jobs import _get_localization_mode, _get_localization_engine


def test_get_localization_mode_mock_default():
    """Test that default mode is 'mock'."""
    with patch.object(settings, "LOCALIZATION_MODE", "mock"):
        assert _get_localization_mode() == "mock"


def test_get_localization_mode_live_lowercase():
    """Test that 'live' mode is recognized (lowercase)."""
    with patch.object(settings, "LOCALIZATION_MODE", "live"):
        assert _get_localization_mode() == "live"


def test_get_localization_mode_live_uppercase():
    """Test that 'LIVE' mode is normalized to 'live' (case-insensitive)."""
    with patch.object(settings, "LOCALIZATION_MODE", "LIVE"):
        assert _get_localization_mode() == "live"


def test_get_localization_mode_live_mixed_case():
    """Test that 'Live' mode is normalized to 'live' (case-insensitive)."""
    with patch.object(settings, "LOCALIZATION_MODE", "Live"):
        assert _get_localization_mode() == "live"


def test_get_localization_mode_invalid_defaults_to_mock():
    """Test that invalid mode values default to 'mock'."""
    with patch.object(settings, "LOCALIZATION_MODE", "invalid"):
        assert _get_localization_mode() == "mock"

    with patch.object(settings, "LOCALIZATION_MODE", ""):
        assert _get_localization_mode() == "mock"


def test_get_localization_engine_mock_mode():
    """Test that mock mode returns None (indicating mock engine)."""
    with patch.object(settings, "LOCALIZATION_MODE", "mock"):
        engine = _get_localization_engine()
        assert engine is None


def test_get_localization_engine_live_mode_with_keys():
    """Test that live mode returns LiveLocalizationEngine when API keys are present."""
    with patch.object(settings, "LOCALIZATION_MODE", "live"):
        with patch.object(settings, "OCR_API_KEY", "test-ocr-key"):
            with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"):
                with patch.object(settings, "OCR_API_ENDPOINT", None):
                    with patch.object(settings, "TRANSLATION_MODEL", "gpt-4o-mini"):
                        with patch("app.routers.jobs.create_live_engine") as mock_create:
                            mock_engine = MagicMock()
                            mock_create.return_value = mock_engine

                            engine = _get_localization_engine()

                            assert engine is not None
                            mock_create.assert_called_once_with(
                                ocr_api_key="test-ocr-key",
                                ocr_api_endpoint=None,
                                openai_api_key="test-openai-key",
                                translation_model="gpt-4o-mini",
                            )


def test_get_localization_engine_live_mode_missing_ocr_key():
    """Test that live mode raises ValueError when OCR_API_KEY is missing."""
    with patch.object(settings, "LOCALIZATION_MODE", "live"):
        with patch.object(settings, "OCR_API_KEY", None):
            with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"):
                with pytest.raises(ValueError) as exc_info:
                    _get_localization_engine()
                assert "OCR_API_KEY is required" in str(exc_info.value)


def test_get_localization_engine_live_mode_missing_openai_key():
    """Test that live mode raises ValueError when OPENAI_API_KEY is missing."""
    with patch.object(settings, "LOCALIZATION_MODE", "live"):
        with patch.object(settings, "OCR_API_KEY", "test-ocr-key"):
            with patch.object(settings, "OPENAI_API_KEY", None):
                with pytest.raises(ValueError) as exc_info:
                    _get_localization_engine()
                assert "OPENAI_API_KEY is required" in str(exc_info.value)


def test_get_localization_engine_live_mode_case_insensitive():
    """Test that live mode works with case-insensitive mode value."""
    with patch.object(settings, "LOCALIZATION_MODE", "LIVE"):
        with patch.object(settings, "OCR_API_KEY", "test-ocr-key"):
            with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"):
                with patch.object(settings, "OCR_API_ENDPOINT", None):
                    with patch.object(settings, "TRANSLATION_MODEL", "gpt-4o-mini"):
                        with patch("app.routers.jobs.create_live_engine") as mock_create:
                            mock_engine = MagicMock()
                            mock_create.return_value = mock_engine

                            engine = _get_localization_engine()

                            assert engine is not None
                            mock_create.assert_called_once()
