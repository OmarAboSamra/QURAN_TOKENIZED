"""
Application configuration using pydantic-settings.

All settings are loaded from environment variables (or a .env file) with
sensible defaults for local development. For production, override via
environment variables or a deployment-specific .env.

Naming convention:
    Python field  "database_url"  <-->  env var  "DATABASE_URL"
    (pydantic-settings handles the case conversion automatically)

Usage:
    from backend.config import get_settings
    settings = get_settings()   # cached singleton via @lru_cache
    print(settings.database_url)
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Groups:
        Environment  – dev/staging/prod toggle
        Database     – SQLite (dev) or PostgreSQL (prod)
        Redis Cache  – optional Redis caching layer
        API          – host, port, CORS, versioning
        Tokenization – paths to Qur'an text and CSV output
        Root Extract – which online sources to query, timeouts
        Celery       – broker/backend URLs for background tasks
        Monitoring   – Prometheus, Sentry (optional)
        Rate Limit   – per-IP request throttling (optional)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently ignore env vars not declared here
    )

    # ── Environment ────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    debug: bool = Field(default=True, description="Debug mode")

    # ── Database ──────────────────────────────────────────────────
    # Default is SQLite for zero-config local development.
    # For production, set DATABASE_URL=postgresql://user:pass@host/dbname
    database_url: str = Field(
        default="sqlite:///./quran.db",
        description="Database connection URL",
    )
    database_pool_size: int = Field(
        default=5,
        description="Database connection pool size",
    )
    database_max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections",
    )

    # ── Redis Cache ────────────────────────────────────────────────
    # Disabled by default. Enable when Redis is available to
    # cache verses, root lookups, and token lists.
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    cache_enabled: bool = Field(
        default=False,
        description="Enable Redis caching",
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds",
    )

    # ── API Server ────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Auto-reload on code changes")
    api_title: str = Field(default="Qur'an Analysis API", description="API title")
    api_version: str = Field(default="0.1.0", description="API version")
    api_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated CORS origins",
    )

    # ── Tokenization Paths ────────────────────────────────────────
    # Input: raw Qur'an text (sura|aya|text per line)
    # Output: CSV of tokenized words for inspection/debugging
    quran_data_path: str = Field(
        default="./data/quran_original_text.txt",
        description="Path to original Qur'an text file",
    )
    output_csv_path: str = Field(
        default="./data/quran_tokens_word.csv",
        description="Path to output CSV file",
    )

    # ── Root Extraction Sources ───────────────────────────────────
    # Comma-separated source names used by RootExtractionService.
    # Available: qurancorpus, tanzil, almaany, baheth, pyarabic, alkhalil
    root_sources: str = Field(
        default="qurancorpus,tanzil,almaany",
        description="Comma-separated list of root extraction sources",
    )
    root_cache_path: str = Field(
        default="./data/quran_roots_cache.json",
        description="Path to root extraction cache",
    )
    root_api_timeout: int = Field(
        default=30,
        description="Timeout for root extraction API calls",
    )

    # ── Celery Background Tasks ───────────────────────────────────
    # Requires a running Redis instance. Separate DB numbers
    # are used for broker (1) and results (2) to avoid conflicts.
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL",
    )
    task_max_retries: int = Field(
        default=3,
        description="Maximum task retries",
    )

    # ── Monitoring (optional) ─────────────────────────────────────
    prometheus_enabled: bool = Field(
        default=False,
        description="Enable Prometheus metrics",
    )
    sentry_dsn: str = Field(
        default="",
        description="Sentry DSN for error tracking",
    )

    # ── Rate Limiting (optional) ──────────────────────────────────
    rate_limit_enabled: bool = Field(
        default=False,
        description="Enable rate limiting",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Requests per minute per IP",
    )

    # ── Logging ───────────────────────────────────────────────────
    # Application Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # ── Derived properties ────────────────────────────────────────
    # Convenience helpers that parse composite fields.

    @property
    def is_sqlite(self) -> bool:
        """True when using SQLite (default local development)."""
        return self.database_url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return "postgresql" in self.database_url

    @property
    def root_sources_list(self) -> list[str]:
        """Return root sources as a list."""
        return [source.strip() for source in self.root_sources.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.api_cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.
    
    @lru_cache ensures the .env file is read only once.
    Call get_settings.cache_clear() to force reload.
    """
    return Settings()
