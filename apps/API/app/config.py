"""
Configuration management for the Media Promo Localizer backend.
"""
import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Localization mode: "mock" (default) or "live"
    LOCALIZATION_MODE: str = os.getenv("LOCALIZATION_MODE", "mock")

    # File upload limits
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024

    # Allowed MIME types
    ALLOWED_MIME_TYPES: List[str] = ["image/jpeg", "image/png"]

    # Job store limits
    MAX_JOBS: int = int(os.getenv("MAX_JOBS", "50"))
    JOB_TTL_SECONDS: int = int(os.getenv("JOB_TTL_SECONDS", "7200"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Analysis settings (for future use)
    ANALYSIS_MAX_LONG_EDGE_PX: int = int(os.getenv("ANALYSIS_MAX_LONG_EDGE_PX", "3072"))

    # OCR provider settings (for live mode)
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "google")
    OCR_API_KEY: Optional[str] = os.getenv("OCR_API_KEY")
    OCR_API_ENDPOINT: Optional[str] = os.getenv("OCR_API_ENDPOINT")

    # Translation provider settings (for live mode)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    TRANSLATION_MODEL: str = os.getenv("TRANSLATION_MODEL", "gpt-4o-mini")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


settings = Settings()


