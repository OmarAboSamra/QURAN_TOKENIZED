"""
Structured logging configuration using structlog.

Provides JSON-formatted logs in production and colored console output
in development. Also includes helper functions for consistent log
records across the application (HTTP requests, DB queries, etc.).

IMPORTANT: configure_logging() must be called once at startup for
structlog processors to be active. Currently this is NOT called
in main.py — flagged for the next optimization pass.

Usage:
    from backend.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("something_happened", key="value")
"""
import logging
import sys
from typing import Any

import structlog

from backend.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Development: Use colored console output
            structlog.dev.ConsoleRenderer()
            if settings.environment == "development"
            # Production: Use JSON output
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> Any:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Request logging middleware helper
def log_request(
    logger: Any,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra: Any,
) -> None:
    """Log HTTP request with structured data."""
    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        **extra,
    )


def log_error(
    logger: Any,
    error: Exception,
    context: str,
    **extra: Any,
) -> None:
    """Log error with structured context."""
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        **extra,
        exc_info=True,
    )


def log_db_query(
    logger: Any,
    query_type: str,
    table: str,
    duration_ms: float,
    **extra: Any,
) -> None:
    """Log database query."""
    logger.debug(
        "db_query",
        query_type=query_type,
        table=table,
        duration_ms=round(duration_ms, 2),
        **extra,
    )


def log_cache_operation(
    logger: Any,
    operation: str,
    key: str,
    hit: bool,
    **extra: Any,
) -> None:
    """Log cache operation."""
    logger.debug(
        "cache_operation",
        operation=operation,
        key=key,
        hit=hit,
        **extra,
    )
