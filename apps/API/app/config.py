"""
Configuration management for the Media Promo Localizer backend.
"""
import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Localization mode: "mock" for Sprint 2
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

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


settings = Settings()

