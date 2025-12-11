"""
Configuration management for the Media Promo Localizer backend.

Environment variable loading precedence:
1. Real environment variables (exported in shell) - highest priority
2. `.env.local` file (for local development only, gitignored)
3. Built-in defaults - lowest priority

Note: `.env.local` is intended for local development only. Secrets in `.env.local`
are gitignored and should never be committed to the repository.
"""
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Localization mode: "mock" (default) or "live"
    LOCALIZATION_MODE: str = Field(default="mock", description="Localization pipeline mode")

    # File upload limits
    MAX_UPLOAD_MB: int = Field(default=20, description="Maximum upload size in MB")
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=20 * 1024 * 1024, description="Maximum upload size in bytes")

    # Allowed MIME types
    ALLOWED_MIME_TYPES: List[str] = Field(default=["image/jpeg", "image/png"])

    # Job store limits
    MAX_JOBS: int = Field(default=50, description="Maximum number of jobs in store")
    JOB_TTL_SECONDS: int = Field(default=7200, description="Job time-to-live in seconds")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Analysis settings (for future use)
    ANALYSIS_MAX_LONG_EDGE_PX: int = Field(default=3072, description="Max long edge for analysis images")

    # OCR provider settings (for live mode)
    OCR_PROVIDER: str = Field(default="google", description="OCR provider name")
    OCR_API_KEY: Optional[str] = Field(default=None, description="OCR provider API key")
    OCR_API_ENDPOINT: Optional[str] = Field(default=None, description="OCR provider API endpoint")

    # Translation provider settings (for live mode)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    TRANSLATION_MODEL: str = Field(default="gpt-4o-mini", description="Translation model name")

    model_config = SettingsConfigDict(
        # Load .env files in order: .env (lower priority) then .env.local (higher priority)
        # Real environment variables (from shell) override both .env files
        # Precedence: shell env vars > .env.local > .env > defaults
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Initialize settings and compute derived fields."""
        super().__init__(**kwargs)
        # Compute MAX_UPLOAD_SIZE_BYTES from MAX_UPLOAD_MB
        self.MAX_UPLOAD_SIZE_BYTES = self.MAX_UPLOAD_MB * 1024 * 1024


settings = Settings()


