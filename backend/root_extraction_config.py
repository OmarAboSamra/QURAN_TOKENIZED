"""
Root Extraction Configuration.

Switch between different root extraction backends here.
"""

# Backend selection
# Options: "legacy" (placeholder algorithmic), "multi-source" (verified API sources)
ROOT_EXTRACTION_BACKEND = "multi-source"  # Using enhanced offline extractors

# Multi-source configuration
# Using offline extractors with improved algorithms (web scraping blocked by sites)
MULTI_SOURCE_ENABLED_EXTRACTORS = [
    "pyarabic",  # PyArabic with database + enhanced algorithm (primary)
    "alkhalil",  # Improved AlKhalil algorithmic (secondary)
]

# Cache configuration
VERIFIED_ROOTS_CACHE_PATH = "data/quran_roots_verified.json"
LEGACY_ROOTS_CACHE_PATH = "data/quran_roots_comprehensive.json"

# API rate limiting (requests per second per source)
API_RATE_LIMIT = 0.67  # ~1.5 seconds between requests per source

# Retry configuration
MAX_RETRIES_PER_SOURCE = 3
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff: 2^attempt seconds

# Confidence thresholds
MIN_CONFIDENCE_FOR_STORAGE = 0.3  # Store roots with at least 30% confidence
HIGH_CONFIDENCE_THRESHOLD = 0.9   # 90%+ means multiple sources agree
