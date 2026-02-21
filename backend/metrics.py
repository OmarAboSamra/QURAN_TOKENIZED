"""
Prometheus metrics for monitoring.

Defines custom counters and histograms for tracking root extraction,
token operations, cache hits/misses, and database query latency.

The helper functions (record_root_extraction, record_token_operation, etc.)
are used by route handlers to emit metrics.

KNOWN ISSUE: get_instrumentator() creates a FastAPI Instrumentator but
it is never wired into the app via instrumentator.instrument(app) in
main.py. The .add() calls also use an incorrect API. This is flagged
for the next optimization pass.
"""
from typing import Optional

from prometheus_client import Counter, Histogram, Info
from prometheus_fastapi_instrumentator import Instrumentator

from backend.config import get_settings

settings = get_settings()

# Application info
app_info = Info("quran_api", "Qur'an Analysis API Information")
app_info.info(
    {
        "version": settings.api_version,
        "environment": settings.environment,
    }
)

# Request metrics (handled by instrumentator)
# Custom business metrics
root_extraction_total = Counter(
    "quran_root_extraction_total",
    "Total number of root extractions performed",
    ["source", "status"],
)

root_extraction_duration = Histogram(
    "quran_root_extraction_duration_seconds",
    "Time spent extracting roots",
    ["source"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

token_operations_total = Counter(
    "quran_token_operations_total",
    "Total token operations",
    ["operation", "status"],
)

cache_operations_total = Counter(
    "quran_cache_operations_total",
    "Total cache operations",
    ["operation", "result"],
)

database_query_duration = Histogram(
    "quran_database_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=[0.001, 0.01, 0.1, 0.5, 1.0],
)


_instrumentator: Optional[Instrumentator] = None


def get_instrumentator() -> Instrumentator:
    """Get FastAPI instrumentator for automatic metrics."""
    global _instrumentator
    if _instrumentator is None:
        _instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="quran_api_requests_inprogress",
            inprogress_labels=True,
        )
        
        # Add custom metrics
        _instrumentator.add(
            Instrumentator.metrics.default(),
            # Add request duration with custom buckets
            Instrumentator.metrics.latency(
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
            ),
        )
    
    return _instrumentator


def record_root_extraction(source: str, status: str, duration: float) -> None:
    """Record root extraction metrics."""
    root_extraction_total.labels(source=source, status=status).inc()
    root_extraction_duration.labels(source=source).observe(duration)


def record_token_operation(operation: str, status: str) -> None:
    """Record token operation."""
    token_operations_total.labels(operation=operation, status=status).inc()


def record_cache_operation(operation: str, result: str) -> None:
    """Record cache operation."""
    cache_operations_total.labels(operation=operation, result=result).inc()


def record_database_query(operation: str, table: str, duration: float) -> None:
    """Record database query."""
    database_query_duration.labels(operation=operation, table=table).observe(duration)
