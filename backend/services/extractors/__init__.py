"""
Extractors package — modular root extraction backends.

Each extractor implements the RootExtractor ABC and provides a single
`extract_root()` method that returns a RootExtractionResult.

Available extractors:
    QuranCorpusExtractor        – scrapes corpus.quran.com
    OfflineCorpusCacheExtractor – reads local corpus_roots_cache.json
    AlMaanyExtractor            – scrapes almaany.com dictionary
    BahethExtractor             – scrapes baheth.info dictionary
    PyArabicExtractor           – uses pyarabic + pattern database
    AlKhalilExtractor           – rule-based morphological stemmer
"""
from backend.services.extractors.base import (
    RootExtractionResult,
    RootExtractor,
    VerifiedRoot,
)
from backend.services.extractors.alkhalil import AlKhalilExtractor
from backend.services.extractors.almaany import AlMaanyExtractor
from backend.services.extractors.baheth import BahethExtractor
from backend.services.extractors.offline_cache import OfflineCorpusCacheExtractor
from backend.services.extractors.pyarabic_ext import PyArabicExtractor
from backend.services.extractors.quran_corpus import QuranCorpusExtractor

__all__ = [
    "RootExtractionResult",
    "RootExtractor",
    "VerifiedRoot",
    "AlKhalilExtractor",
    "AlMaanyExtractor",
    "BahethExtractor",
    "OfflineCorpusCacheExtractor",
    "PyArabicExtractor",
    "QuranCorpusExtractor",
]
