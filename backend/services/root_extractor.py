"""Root extraction service with support for multiple online sources."""
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class RootExtractionResult:
    """Result from a root extraction attempt."""

    word: str
    root: Optional[str]
    source: str
    success: bool
    error: Optional[str] = None


class RootExtractor(ABC):
    """Abstract base class for root extractors."""

    def __init__(self, name: str) -> None:
        """Initialize extractor with a name."""
        self.name = name

    @abstractmethod
    async def extract_root(self, word: str) -> RootExtractionResult:
        """
        Extract the Arabic root for a given word.
        
        Args:
            word: Normalized Arabic word
            
        Returns:
            RootExtractionResult with the extracted root or error
        """
        pass


class QuranCorpusExtractor(RootExtractor):
    """
    Extract roots from Quranic Arabic Corpus.
    
    Uses the morphology data from corpus.quran.com.
    """

    def __init__(self) -> None:
        """Initialize QuranCorpus extractor."""
        super().__init__("qurancorpus")
        self.base_url = "https://corpus.quran.com/wordmorphology.jsp"
        
        # Load comprehensive roots from cache file
        self.fallback_roots = self._load_roots_cache()
        
    def _load_roots_cache(self) -> dict:
        """Load roots from comprehensive cache file."""
        cache_path = Path(__file__).parent.parent.parent / "data" / "quran_roots_comprehensive.json"
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract root values from nested structure
                    # Format: {word: {"placeholder": root}} or {word: {"qurancorpus": root}}
                    roots_dict = {}
                    for word, sources in data.items():
                        if isinstance(sources, dict):
                            # Get first available root from any source
                            root = sources.get('qurancorpus') or sources.get('placeholder')
                            if root:
                                roots_dict[word] = root
                        elif isinstance(sources, str):
                            roots_dict[word] = sources
                    return roots_dict
            except Exception as e:
                print(f"[WARNING] Failed to load comprehensive roots: {e}")
                return self._get_fallback_roots()
        else:
            print(f"[WARNING] Comprehensive roots file not found at {cache_path}")
            return self._get_fallback_roots()
    
    def _get_fallback_roots(self) -> dict:
        """Get minimal fallback roots for basic functionality."""
        return {
            # Surah 1: Al-Fatiha
            "بسم": "سمو",
            "الله": "اله",
            "الرحمن": "رحم",
            "الرحيم": "رحم",
            "الحمد": "حمد",
            "لله": "اله",
            "رب": "ربب",
            "العلمين": "علم",
            "ملك": "ملك",
            "مالك": "ملك",
            "يوم": "يوم",
            "الدين": "دين",
            "اياك": "اتي",
            "نعبد": "عبد",
            "واياك": "اتي",
            "نستعين": "عون",
            "اهدنا": "هدي",
            "الصرط": "صرط",
            "الصراط": "صرط",
            "المستقيم": "قوم",
            "صرط": "صرط",
            "صراط": "صرط",
            "الذين": "الذ",
            "انعمت": "نعم",
            "عليهم": "علو",
            "غير": "غير",
            "المغضوب": "غضب",
            "ولا": "ولا",
            "الضالين": "ضلل",
            # Surah 2: Al-Baqarah (sample words)
            "الم": "الم",  # Mysterious letters (muqatta'at)
            "ذلك": "ذلك",
            "الكتب": "كتب",
            "كتب": "كتب",
            "لا": "لا",
            "ريب": "ريب",
            "فيه": "فيه",
            "هدي": "هدي",
            "للمتقين": "وقي",
            "متقين": "وقي",
            "الذين": "الذ",
            "يومنون": "امن",
            "بالغيب": "غيب",
            "غيب": "غيب",
            "ويقيمون": "قوم",
            "قيمون": "قوم",
            "الصلوة": "صلو",
            "صلوة": "صلو",
            "ومما": "ممم",
            "رزقنهم": "رزق",
            "رزق": "رزق",
            "ينفقون": "نفق",
            "نفقون": "نفق",
        }

    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root from Quranic Arabic Corpus."""
        try:
            # Try fallback first (for demo purposes)
            if word in self.fallback_roots:
                return RootExtractionResult(
                    word=word,
                    root=self.fallback_roots[word],
                    source=self.name,
                    success=True,
                )
            
            # Attempt real API call (commented out by default)
            # async with httpx.AsyncClient(timeout=10.0) as client:
            #     # Example: Search for word in corpus
            #     response = await client.get(
            #         f"{self.base_url}",
            #         params={"location": "1:1"}  # Adjust based on actual API
            #     )
            #     if response.status_code == 200:
            #         # Parse HTML/JSON response to extract root
            #         # This would require BeautifulSoup or similar
            #         root = self._parse_corpus_response(response.text, word)
            #         return RootExtractionResult(
            #             word=word,
            #             root=root,
            #             source=self.name,
            #             success=True,
            #         )
            
            # If not in fallback and API not implemented, return None
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error="Word not in fallback dictionary",
            )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )


class TanzilExtractor(RootExtractor):
    """
    Extract roots from Tanzil project data.
    
    Note: This is a placeholder implementation.
    """

    def __init__(self) -> None:
        """Initialize Tanzil extractor."""
        super().__init__("tanzil")

    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root from Tanzil data."""
        try:
            # TODO: Implement actual extraction logic
            # This could use local data files from Tanzil project
            
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error="Not implemented yet",
            )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )


class AlmaanyExtractor(RootExtractor):
    """
    Extract roots from Almaany Arabic dictionary.
    
    Note: This is a placeholder implementation.
    """

    def __init__(self) -> None:
        """Initialize Almaany extractor."""
        super().__init__("almaany")
        self.base_url = "https://www.almaany.com"

    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root from Almaany."""
        try:
            # TODO: Implement actual API call or web scraping
            
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error="Not implemented yet",
            )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )


class RootExtractionService:
    """
    Service for extracting Arabic roots from multiple sources.
    
    This service:
    - Manages multiple root extraction sources
    - Queries sources in parallel
    - Caches results to minimize API calls
    """

    def __init__(self, cache_path: Optional[Path] = None) -> None:
        """
        Initialize root extraction service.
        
        Args:
            cache_path: Path to cache file for storing results
        """
        self.extractors: dict[str, RootExtractor] = {
            "qurancorpus": QuranCorpusExtractor(),
            "tanzil": TanzilExtractor(),
            "almaany": AlmaanyExtractor(),
        }
        
        self.cache_path = cache_path
        self.cache: dict[str, dict[str, Optional[str]]] = {}
        
        if cache_path and cache_path.exists():
            self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file."""
        if self.cache_path and self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                print(f"[OK] Loaded cache with {len(self.cache)} entries")
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        if self.cache_path:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_path, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
                print(f"[OK] Saved cache with {len(self.cache)} entries")
            except Exception as e:
                print(f"Warning: Could not save cache: {e}")

    async def extract_root_multi_source(
        self,
        word: str,
        sources: Optional[list[str]] = None,
    ) -> dict[str, RootExtractionResult]:
        """
        Extract root from multiple sources in parallel.
        
        Args:
            word: Normalized Arabic word
            sources: List of source names to use (default: all)
            
        Returns:
            Dictionary mapping source name to extraction result
        """
        # Check cache first
        if word in self.cache:
            return {
                source: RootExtractionResult(
                    word=word,
                    root=root,
                    source=source,
                    success=root is not None,
                )
                for source, root in self.cache[word].items()
            }
        
        # Determine which extractors to use
        if sources is None:
            extractors_to_use = self.extractors.values()
        else:
            extractors_to_use = [
                self.extractors[s] for s in sources if s in self.extractors
            ]
        
        # Query all sources in parallel
        tasks = [extractor.extract_root(word) for extractor in extractors_to_use]
        results = await asyncio.gather(*tasks)
        
        # Store in cache
        self.cache[word] = {
            result.source: result.root for result in results if result.success
        }
        
        return {result.source: result for result in results}

    def save_cache(self) -> None:
        """Public method to save cache."""
        self._save_cache()

    def extract_root_sync(self, word: str) -> Optional[dict]:
        """
        Synchronous wrapper for root extraction (for Celery tasks).
        
        Args:
            word: Normalized Arabic word
            
        Returns:
            Dictionary with "root" and "sources" keys, or None if extraction fails
        """
        try:
            # Run async method in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    self.extract_root_multi_source(word)
                )
                
                # Find the first successful result
                for source, result in results.items():
                    if result.success and result.root:
                        return {
                            "root": result.root,
                            "sources": {source: result.root},
                        }
                
                # No successful extraction
                return None
                
            finally:
                loop.close()
                
        except Exception as e:
            print(f"Error extracting root for '{word}': {e}")
            return None
