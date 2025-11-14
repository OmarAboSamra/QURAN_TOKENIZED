"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Database Configuration
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

    # Redis Cache Configuration
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

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Auto-reload on code changes")
    api_title: str = Field(default="Qur'an Analysis API", description="API title")
    api_version: str = Field(default="0.1.0", description="API version")
    api_cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated CORS origins",
    )

    # Tokenization Settings
    quran_data_path: str = Field(
        default="./data/quran_original_text.txt",
        description="Path to original Qur'an text file",
    )
    output_csv_path: str = Field(
        default="./data/quran_tokens_word.csv",
        description="Path to output CSV file",
    )

    # Root Extraction Sources
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

    # Background Tasks
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

    # Monitoring
    prometheus_enabled: bool = Field(
        default=False,
        description="Enable Prometheus metrics",
    )
    sentry_dsn: str = Field(
        default="",
        description="Sentry DSN for error tracking",
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(
        default=False,
        description="Enable rate limiting",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Requests per minute per IP",
    )

    # Application Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return "postgresql" in self.database_url

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
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
    """Get cached settings instance."""
    return Settings()
