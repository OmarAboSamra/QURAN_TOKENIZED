"""
AlKhalilExtractor — rule-based morphological root extraction.

Uses classical Arabic morphology rules (prefix/suffix stripping,
weak-letter handling, deduplication) to isolate the root from
inflected word forms.
"""
import re
from typing import Optional

from backend.services.extractors.base import RootExtractionResult, RootExtractor

# Import pyarabic helpers
try:
    from pyarabic.araby import strip_tashkeel, strip_tatweel
except ImportError:  # pragma: no cover
    strip_tashkeel = lambda x: x  # type: ignore[assignment]
    strip_tatweel = lambda x: x  # type: ignore[assignment]


class AlKhalilExtractor(RootExtractor):
    """
    Extract roots using AlKhalil Morpho Sys algorithm.

    This is a rule-based approach for Arabic morphology based on
    well-known patterns in Arabic grammar.
    """

    def __init__(self) -> None:
        super().__init__("alkhalil")
        self._load_pattern_rules()

    def _load_pattern_rules(self) -> None:
        """Load Arabic morphological patterns."""
        self.prefixes: list[str] = [
            "والذي", "بالذي", "فالذي", "كالذي",
            "وال", "فال", "بال", "كال", "لل",
            "ال", "و", "ف", "ب", "ل", "ك",
        ]
        self.suffixes: list[str] = [
            "ونهم", "ونها", "ونني", "ونكم",
            "ونه", "ونا", "وني", "ومه", "وما",
            "تهم", "تها", "تني", "تكم", "تنا",
            "هما", "كما", "نني",
            "ون", "ين", "ان", "ات", "ية",
            "ته", "تا", "تي", "تك", "تم", "تن",
            "ها", "هم", "هن", "كم", "كن", "نا",
            "ة", "ه", "ي", "ك", "ن", "ا", "ت",
        ]
        self.weak_letters: set[str] = set('اويءى')

    async def extract_root(self, word: str, **kwargs) -> RootExtractionResult:
        """Extract root using morphological rules with improved accuracy."""
        try:
            cleaned: str = strip_tashkeel(strip_tatweel(word))

            # Remove prefixes (longest first)
            stem = cleaned
            prefix_removed = ""
            for prefix in self.prefixes:
                if stem.startswith(prefix) and len(stem) > len(prefix) + 2:
                    prefix_removed = prefix
                    stem = stem[len(prefix):]
                    break

            # Remove suffixes (longest first)
            for suffix in self.suffixes:
                if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
                    stem = stem[: -len(suffix)]
                    break

            # Weak letter at start after prefix removal might be affix
            if prefix_removed and stem and stem[0] in self.weak_letters:
                if len(stem) > 3 and stem[1] not in self.weak_letters:
                    stem = stem[1:]

            # Remove consecutive duplicates (keep one copy)
            deduplicated = ''
            prev_char = ''
            for char in stem:
                if char != prev_char or char in self.weak_letters:
                    deduplicated += char
                prev_char = char

            stem = deduplicated if len(deduplicated) >= 3 else stem

            # Extract root (3-4 letters)
            root: Optional[str] = None
            if len(stem) >= 3:
                if len(stem) == 3:
                    root = stem
                elif len(stem) == 4:
                    if stem[-1] in self.weak_letters and stem[-2] not in self.weak_letters:
                        root = stem[:3]
                    else:
                        root = stem[:4]
                else:
                    strong_letters = [c for c in stem if c not in self.weak_letters]
                    if len(strong_letters) >= 3:
                        root = ''.join(strong_letters[:3])
                    else:
                        root = stem[:4] if len(stem) >= 4 else stem[:3]

                if root and 2 <= len(root) <= 4 and re.match(r'^[\u0600-\u06FF]+$', root):
                    return RootExtractionResult(
                        word=word,
                        root=root,
                        source=self.name,
                        success=True,
                        confidence=0.4,
                    )

            # Fallback: return stem if reasonable length
            if 2 <= len(stem) <= 4:
                return RootExtractionResult(
                    word=word,
                    root=stem,
                    source=self.name,
                    success=True,
                    confidence=0.3,
                )

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
