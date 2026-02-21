"""
RootExtractionService — high-level API for root extraction.

Orchestrates the extraction pipeline:
    1. Try offline corpus cache first (instant, 100 % accurate for Quran)
    2. Fall back to online corpus if cache miss
    3. Fall back to algorithmic extractors with multi-source verification
    4. Save verified results to cache
"""
import asyncio
from pathlib import Path
from typing import Optional

from backend.services.extractors.alkhalil import AlKhalilExtractor
from backend.services.extractors.offline_cache import OfflineCorpusCacheExtractor
from backend.services.extractors.pyarabic_ext import PyArabicExtractor
from backend.services.extractors.quran_corpus import QuranCorpusExtractor
from backend.services.multi_source_verifier import MultiSourceVerifier


class RootExtractionService:
    """
    Main service for root extraction with multi-source verification.
    """

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        corpus_cache_path: Optional[Path] = None,
    ) -> None:
        if corpus_cache_path is None:
            corpus_cache_path = Path(__file__).parent.parent.parent / "data" / "corpus_roots_cache.json"
        self.offline_corpus = OfflineCorpusCacheExtractor(corpus_cache_path)
        self.corpus_extractor = QuranCorpusExtractor()

        offline_extractors = [
            PyArabicExtractor(),
            AlKhalilExtractor(),
        ]

        self.verifier = MultiSourceVerifier(offline_extractors, cache_path)

    async def extract_root(
        self,
        word: str,
        sura: Optional[int] = None,
        aya: Optional[int] = None,
        position: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Extract and verify root for a word.

        Args:
            word: Normalized Arabic word
            sura: Sura number (optional, enables corpus extractors)
            aya: Aya number (optional, enables corpus extractors)
            position: Word position in verse (optional, enables corpus extractors)

        Returns:
            Dictionary with root and source information, or None if failed
        """
        # Priority 1: offline corpus cache
        if sura is not None and aya is not None and position is not None:
            try:
                offline_result = await self.offline_corpus.extract_root(word, sura=sura, aya=aya, position=position)
                if offline_result.success and offline_result.root:
                    return {
                        'root': offline_result.root,
                        'sources': {offline_result.source: offline_result.root},
                        'confidence': offline_result.confidence,
                        'agreement': "1/1",
                        'method': 'offline_cache',
                    }
            except Exception as e:
                print(f"[RootExtractionService] Offline cache lookup failed: {e}")

            # Priority 2: online corpus
            try:
                corpus_result = await self.corpus_extractor.extract_root(
                    word, sura=sura, aya=aya, position=position,
                )
                if corpus_result.success and corpus_result.root:
                    return {
                        'root': corpus_result.root,
                        'sources': {corpus_result.source: corpus_result.root},
                        'confidence': corpus_result.confidence,
                        'agreement': "1/1",
                        'method': 'online_corpus',
                    }
            except Exception as e:
                print(f"[RootExtractionService] Online corpus extraction failed: {e}")

        # Priority 3: algorithmic with multi-source verification
        verified = await self.verifier.verify_root(word)
        if verified:
            return {
                'root': verified.root,
                'sources': verified.sources,
                'confidence': verified.confidence,
                'agreement': f"{verified.agreement_count}/{verified.total_sources}",
                'method': 'algorithmic',
            }
        return None

    def extract_root_sync(
        self,
        word: str,
        sura: Optional[int] = None,
        aya: Optional[int] = None,
        position: Optional[int] = None,
    ) -> Optional[dict]:
        """Synchronous wrapper for Celery tasks."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.extract_root(word, sura, aya, position),
                )
            finally:
                loop.close()
        except Exception as e:
            print(f"[RootExtractionService] Error extracting root for '{word}': {e}")
            return None

    def save_cache(self) -> None:
        """Save verified roots cache."""
        self.verifier.save_cache()


def extract_root_sync(word: str) -> Optional[dict]:
    """
    Standalone function for root extraction (backward compatible).
    """
    cache_path = Path(__file__).parent.parent.parent / "data" / "quran_roots_verified.json"
    service = RootExtractionService(cache_path)
    result = service.extract_root_sync(word)
    service.save_cache()
    return result
