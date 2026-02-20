"""
Root Extraction Configuration.
"""

# Enabled extractors (order = priority)
ENABLED_EXTRACTORS = [
    "pyarabic",   # PyArabic with database + enhanced algorithm (primary)
    "alkhalil",   # AlKhalil algorithmic (secondary)
]

# Cache paths
VERIFIED_ROOTS_CACHE_PATH = "data/quran_roots_verified.json"

# API rate limiting (seconds between requests per source)
API_RATE_LIMIT = 1.5

# Retry configuration
MAX_RETRIES_PER_SOURCE = 3
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff: 2^attempt seconds

# Confidence thresholds
MIN_CONFIDENCE_FOR_STORAGE = 0.3  # Store roots with at least 30% confidence
HIGH_CONFIDENCE_THRESHOLD = 0.9   # 90%+ means multiple sources agree
