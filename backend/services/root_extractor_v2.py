"""
Multi-source Arabic root extraction with verification.

BACKWARD-COMPATIBILITY SHIM
============================
This file formerly contained the monolithic 1200-line implementation.
As of the C4 refactoring, the code has been split into focused modules
under `backend.services.extractors` and two new service files:

    extractors/base.py         - RootExtractionResult, VerifiedRoot, RootExtractor ABC
    extractors/quran_corpus.py - QuranCorpusExtractor
    extractors/offline_cache.py- OfflineCorpusCacheExtractor
    extractors/almaany.py      - AlMaanyExtractor
    extractors/baheth.py       - BahethExtractor
    extractors/pyarabic_ext.py - PyArabicExtractor
    extractors/alkhalil.py     - AlKhalilExtractor
    multi_source_verifier.py   - MultiSourceVerifier
    root_extraction_service.py - RootExtractionService + extract_root_sync()

All public names are re-exported here so that existing imports like
`from backend.services.root_extractor_v2 import RootExtractionService`
continue to work without modification.
"""

# Re-export everything from the new split modules
from backend.services.extractors.base import (          # noqa: F401
    RootExtractionResult,
    RootExtractor,
    VerifiedRoot,
)
from backend.services.extractors.quran_corpus import (  # noqa: F401
    QuranCorpusExtractor,
)
from backend.services.extractors.offline_cache import ( # noqa: F401
    OfflineCorpusCacheExtractor,
)
from backend.services.extractors.almaany import (       # noqa: F401
    AlMaanyExtractor,
)
from backend.services.extractors.baheth import (        # noqa: F401
    BahethExtractor,
)
from backend.services.extractors.pyarabic_ext import (  # noqa: F401
    PyArabicExtractor,
)
from backend.services.extractors.alkhalil import (      # noqa: F401
    AlKhalilExtractor,
)
from backend.services.multi_source_verifier import (    # noqa: F401
    MultiSourceVerifier,
)
from backend.services.root_extraction_service import (  # noqa: F401
    RootExtractionService,
    extract_root_sync,
)

__all__ = [
    "RootExtractionResult",
    "RootExtractor",
    "VerifiedRoot",
    "QuranCorpusExtractor",
    "OfflineCorpusCacheExtractor",
    "AlMaanyExtractor",
    "BahethExtractor",
    "PyArabicExtractor",
    "AlKhalilExtractor",
    "MultiSourceVerifier",
    "RootExtractionService",
    "extract_root_sync",
]
