"""
Base classes and data types for root extraction.

Defines the abstract RootExtractor interface that all extraction
backends implement, plus the RootExtractionResult and VerifiedRoot
data containers used throughout the extraction pipeline.
"""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class RootExtractionResult:
    """Result from a single root extraction attempt."""

    word: str
    root: Optional[str]
    source: str
    success: bool
    confidence: float = 0.0
    error: Optional[str] = None


@dataclass
class VerifiedRoot:
    """Verified root with consensus from multiple sources."""

    word: str
    root: str
    sources: dict[str, str]  # source name → extracted root
    confidence: float
    agreement_count: int
    total_sources: int


class RootExtractor(ABC):
    """Abstract base class for root extractors."""

    def __init__(self, name: str) -> None:
        """Initialize extractor with a name."""
        self.name = name
        self.last_request_time: float = 0.0
        self.min_request_interval: float = 1.0  # seconds between requests

    async def rate_limit(self) -> None:
        """Implement rate limiting to respect server limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    @abstractmethod
    async def extract_root(self, word: str, **kwargs) -> RootExtractionResult:
        """Extract root for a word.  Must be implemented by subclasses."""
        ...
