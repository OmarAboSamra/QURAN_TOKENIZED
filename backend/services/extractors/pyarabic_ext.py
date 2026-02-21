"""
PyArabicExtractor — database + algorithmic root extraction using pyarabic.

Uses a known-roots database (from quran_roots_comprehensive.json) for
high-confidence lookups, falling back to an affix-stripping algorithm.
"""
import json
import re
from pathlib import Path
from typing import Optional

from backend.services.extractors.base import RootExtractionResult, RootExtractor

# Import pyarabic for morphological analysis
try:
    from pyarabic.araby import strip_tashkeel, strip_tatweel
except ImportError:  # pragma: no cover
    strip_tashkeel = lambda x: x  # type: ignore[assignment]
    strip_tatweel = lambda x: x  # type: ignore[assignment]


class PyArabicExtractor(RootExtractor):
    """
    Extract roots using PyArabic library.

    PyArabic provides advanced Arabic morphological analysis including
    root extraction using linguistic rules.
    """

    def __init__(self) -> None:
        super().__init__("pyarabic")
        self.known_roots: dict[str, str] = {}
        self._load_root_database()

    def _load_root_database(self) -> None:
        """Load known roots database from comprehensive file."""
        cache_path = Path(__file__).parent.parent.parent.parent / "data" / "quran_roots_comprehensive.json"

        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data: dict = json.load(f)
                    for word, sources in data.items():
                        if isinstance(sources, dict):
                            root = sources.get("placeholder") or sources.get("qurancorpus")
                            if root:
                                self.known_roots[word] = root
            except Exception as e:
                print(f"[{self.name}] Warning: Could not load root database: {e}")

    def _extract_root_algorithmic(self, word: str) -> Optional[str]:
        """Extract root using improved affix-stripping algorithm."""
        cleaned: str = strip_tashkeel(strip_tatweel(word))

        # Common prefixes (most common first)
        prefixes = [
            'وال', 'فال', 'بال', 'كال', 'لال',
            'ال',
            'و', 'ف', 'ب', 'ل', 'ك',
        ]

        # Common suffixes (most common first)
        suffixes = [
            'ونهم', 'ونها', 'ونكم',
            'ونه', 'ونا', 'وني', 'ومه', 'وما', 'ومي',
            'ون', 'ين', 'ان', 'ات', 'ية', 'تين',
            'ته', 'تا', 'تي', 'تك', 'تم', 'تن',
            'ها', 'هم', 'هن', 'كم', 'كن', 'نا',
            'ة', 'ه', 'ي', 'ك', 'ن', 'ا',
        ]

        # Remove prefixes
        stem = cleaned
        for prefix in prefixes:
            if stem.startswith(prefix) and len(stem) > len(prefix) + 2:
                stem = stem[len(prefix):]
                break

        # Remove suffixes
        for suffix in suffixes:
            if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
                stem = stem[: -len(suffix)]
                break

        # Remove weak letters from edges in certain contexts
        if len(stem) > 3:
            if stem[0] in 'اوي' and stem[1] not in 'اويء' and stem[2] not in 'اويء':
                stem = stem[1:]
            if len(stem) > 3 and stem[-1] in 'ايوى' and stem[-2] not in 'اويء':
                stem = stem[:-1]

        # Extract root (typically 3 letters, sometimes 4)
        if len(stem) >= 3:
            if len(stem) == 3:
                root = stem
            elif len(stem) == 4:
                if stem[-1] == 'ن' and cleaned != word:
                    root = stem[:3]
                else:
                    root = stem
            else:
                strong = [c for c in stem if c not in 'اويءى']
                root = ''.join(strong[:3]) if len(strong) >= 3 else stem[:3]

            return root if len(root) >= 2 else None

        return stem if len(stem) >= 2 else None

    async def extract_root(self, word: str, **kwargs) -> RootExtractionResult:
        """Extract root using PyArabic enhanced algorithm."""
        try:
            # Check known roots first
            if word in self.known_roots:
                return RootExtractionResult(
                    word=word,
                    root=self.known_roots[word],
                    source=self.name,
                    success=True,
                    confidence=0.7,
                )

            root = self._extract_root_algorithmic(word)

            if root and len(root) >= 2:
                return RootExtractionResult(
                    word=word,
                    root=root,
                    source=self.name,
                    success=True,
                    confidence=0.6,
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Could not extract valid root",
                )

        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )
