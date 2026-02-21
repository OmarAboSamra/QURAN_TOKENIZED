"""
OfflineCorpusCacheExtractor — instant lookups from a pre-built JSON cache.

Benefits:
    - Zero network requests
    - Instant lookups
    - 100 % accuracy for Quranic words
    - Authoritative fallback

Build the cache with ``scripts/build_corpus_cache.py``.
"""
import json
from pathlib import Path
from typing import Any, Optional

from backend.services.extractors.base import RootExtractionResult, RootExtractor


class OfflineCorpusCacheExtractor(RootExtractor):
    """
    Extract roots from offline corpus cache (pre-built from corpus.quran.com).
    """

    def __init__(self, cache_path: Path) -> None:
        super().__init__("offline_corpus_cache")
        self.cache_path = cache_path
        self.cache: dict[str, str] = {}
        self.metadata: dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load the offline corpus cache from disk."""
        try:
            if not self.cache_path.exists():
                print(f"[{self.name}] Cache file not found: {self.cache_path}")
                print(f"[{self.name}] Run scripts/build_corpus_cache.py to create cache")
                return

            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data: dict = json.load(f)

            self.metadata = data.get('metadata', {})
            self.cache = data.get('roots', {})

            print(f"[{self.name}] Loaded cache from {self.cache_path}")
            print(f"[{self.name}] Total words: {self.metadata.get('total_words', len(self.cache))}")

        except Exception as e:
            print(f"[{self.name}] Error loading cache: {e}")
            self.cache = {}

    async def extract_root(
        self,
        word: str,
        sura: Optional[int] = None,
        aya: Optional[int] = None,
        position: Optional[int] = None,
        **kwargs,
    ) -> RootExtractionResult:
        """
        Extract root from offline cache.

        Args:
            word: Arabic word (for error messages)
            sura: Sura number (required)
            aya: Aya number (required)
            position: Word position in verse (0-indexed, required)
        """
        if sura is None or aya is None or position is None:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error="sura, aya, and position are required for cache extractor",
            )

        try:
            key = f"{sura}:{aya}:{position}"
            root = self.cache.get(key)

            if root:
                return RootExtractionResult(
                    word=word,
                    root=root,
                    source=self.name,
                    success=True,
                    confidence=1.0,
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error=f"Position {key} not found in cache",
                )

        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )
