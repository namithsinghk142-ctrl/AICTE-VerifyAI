"""Application configuration loaded from environment variables."""

from __future__ import annotations
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — values are read from .env / environment."""

    # Application metadata
    app_title: str = "AICTE VerifyAI"
    app_version: str = "0.6.0"
    app_env: str = "development"
    app_debug: bool = False

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Database
    database_url: str = "sqlite:////tmp/aicte-verifyai.db" if os.getenv("VERCEL") else "sqlite:///./verifyai.db"

    # CORS — comma-separated list of allowed origins
    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    # Document storage & upload limits
    storage_dir: str = "/tmp/aicte-verifyai-storage" if os.getenv("VERCEL") else "./storage"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB default

    # OCR configuration
    tesseract_cmd: str | None = None

    # Anomaly detection & similarity configuration (Phase 4)
    near_duplicate_similarity_threshold: float = 0.85
    enable_anomaly_detection: bool = True

    # Issuer verification & regulatory compliance assistance (Phase 5)
    issuer_verification_provider: str = "mock"
    mock_issuer_provider_available: bool = True
    enable_compliance_assistance: bool = True

    # Google OAuth 2.0 / OpenID Connect (Phase 7 - Authentication)
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = "http://localhost:5173"

    # Administrator-controlled allowlist (comma-separated, normalized lowercase)
    # Only approved emails may establish an active authenticated session
    approved_emails: str = "adhav.sri123@gmail.com,namithsceptile142@gmail.com"

    # Authentication Token & Security
    token_secret: str = "sih-verifyai-dev-secret-do-not-use-in-production-2026"
    token_ttl_seconds: int = 8 * 60 * 60  # 8 hours

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def approved_email_list(self) -> list[str]:
        """Parse the normalized comma-separated approved emails list."""
        return [e.strip().lower() for e in self.approved_emails.split(",") if e.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    """Factory that returns a settings instance.

    Using a plain function makes it easy to override in tests.
    """
    return Settings()
