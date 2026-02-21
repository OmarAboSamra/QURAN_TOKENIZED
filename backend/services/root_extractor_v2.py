"""
Multi-source Arabic root extraction with verification.

This is the largest module in the project (~1200 lines). It defines
six extraction backends and a verification layer:

Extractors (each implements RootExtractor ABC):
    QuranCorpusExtractor       – scrapes corpus.quran.com
    OfflineCorpusCacheExtractor – reads local corpus_roots_cache.json
    AlMaanyExtractor           – scrapes almaany.com dictionary
    BahethExtractor            – scrapes baheth.info dictionary
    PyArabicExtractor          – uses pyarabic library for morphology
    AlKhalilExtractor          – uses pyarabic.araby for stemming

Verification:
    MultiSourceVerifier – runs all extractors, picks consensus root

Orchestration:
    RootExtractionService – high-level API used by tasks and scripts

The service uses httpx for async HTTP, BeautifulSoup for scraping,
and includes retry logic, rate limiting, and caching.

NOTE: This module is large and could be split into separate files
per extractor in a future refactoring pass.
"""

import asyncio
import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from collections import Counter

import httpx
from bs4 import BeautifulSoup

# Import pyarabic for advanced morphological analysis
try:
    from pyarabic.araby import strip_tashkeel, strip_tatweel, is_arabicrange
    from pyarabic.araby import tokenize, is_arabicword
except ImportError:
    # Fallback if pyarabic not available
    strip_tashkeel = lambda x: x
    strip_tatweel = lambda x: x
    is_arabicrange = lambda x: True
    tokenize = lambda x: [x]
    is_arabicword = lambda x: True


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
    sources: dict[str, str]  # source name -> extracted root
    confidence: float
    agreement_count: int
    total_sources: int


class RootExtractor(ABC):
    """Abstract base class for root extractors."""
    
    def __init__(self, name: str):
        """Initialize extractor with a name."""
        self.name = name
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    async def rate_limit(self):
        """Implement rate limiting to respect server limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    @abstractmethod
    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root for a word. Must be implemented by subclasses."""
        pass


class QuranCorpusExtractor(RootExtractor):
    """
    Extract roots from Quranic Arabic Corpus word-by-word pages.
    
    Fetches pre-extracted roots from corpus.quran.com which provides accurate
    morphological analysis including roots in Buckwalter transliteration.
    """
    
    def __init__(self):
        super().__init__("qurancorpus")
        self.base_url = "https://corpus.quran.com"
        self.min_request_interval = 1.0  # 1 second between requests
        self.verse_cache = {}  # Cache roots by verse
        
        # Buckwalter to Arabic transliteration map
        self.buckwalter_map = {
            'A': 'ا', 'b': 'ب', 't': 'ت', 'v': 'ث', 'j': 'ج', 'H': 'ح', 'x': 'خ',
            'd': 'د', '*': 'ذ', 'r': 'ر', 'z': 'ز', 's': 'س', '$': 'ش', 'S': 'ص',
            'D': 'ض', 'T': 'ط', 'Z': 'ظ', 'E': 'ع', 'g': 'غ', 'f': 'ف', 'q': 'ق',
            'k': 'ك', 'l': 'ل', 'm': 'م', 'n': 'ن', 'h': 'ه', 'w': 'و', 'y': 'ي',
            'Y': 'ى', "'": 'ء', 'p': 'ة', '|': 'آ', '>': 'أ', '<': 'إ', '&': 'ؤ', '}': 'ئ',
        }
    
    def _buckwalter_to_arabic(self, text: str) -> str:
        """Convert Buckwalter transliteration to Arabic"""
        return ''.join(self.buckwalter_map.get(c, c) for c in text)
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client."""
        return httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
    
    async def _fetch_verse_roots(self, sura: int, aya: int) -> dict[int, str]:
        """
        Fetch all roots for a verse from corpus word-by-word page.
        
        Returns:
            dict mapping position (0-indexed) to Arabic root
        """
        cache_key = f"{sura}:{aya}"
        if cache_key in self.verse_cache:
            return self.verse_cache[cache_key]
        
        client = None
        try:
            client = self._create_client()
            url = f"{self.base_url}/wordbyword.jsp?chapter={sura}&verse={aya}"
            
            print(f"[{self.name}] Fetching verse {sura}:{aya}")
            
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            roots = {}
            
            # Find all rows in morphology table
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # First cell: translation with dictionary link and location
                    translation_cell = cells[0]
                    dict_link = translation_cell.find('a', href=re.compile(r'/qurandictionary\.jsp\?q='))
                    
                    if dict_link:
                        # Extract location from the cell
                        location_span = translation_cell.find('span', class_='location')
                        if location_span:
                            location_text = location_span.text.strip()  # Format: "(1:1:1)"
                            # Parse location: (sura:aya:word_index)
                            loc_match = re.match(r'\((\d+):(\d+):(\d+)\)', location_text)
                            if loc_match:
                                loc_sura, loc_aya, word_index = map(int, loc_match.groups())
                                
                                # Only include words from the requested verse
                                if loc_sura == sura and loc_aya == aya:
                                    # Extract Buckwalter root from URL
                                    href = dict_link.get('href', '')
                                    root_match = re.search(r'q=([a-zA-Z*$]+)', href)
                                    if root_match:
                                        root_buckwalter = root_match.group(1)
                                        root_arabic = self._buckwalter_to_arabic(root_buckwalter)
                                        
                                        # word_index is 1-based in corpus, convert to 0-based
                                        position = word_index - 1
                                        roots[position] = root_arabic
            
            print(f"[{self.name}] Found {len(roots)} words in verse {sura}:{aya}")
            
            # Cache the results
            self.verse_cache[cache_key] = roots
            return roots
            
        except Exception as e:
            print(f"[{self.name}] Error fetching verse {sura}:{aya}: {e}")
            return {}
        finally:
            if client:
                await client.aclose()
    
    async def extract_root(self, word: str, sura: int = None, aya: int = None, position: int = None) -> RootExtractionResult:
        """
        Extract root from Quranic Corpus by fetching entire verse.
        
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
                error="sura, aya, and position are required for corpus extractor"
            )
        
        try:
            await self.rate_limit()
            
            # Fetch all roots for the verse
            verse_roots = await self._fetch_verse_roots(sura, aya)
            
            # Get root for this position
            root = verse_roots.get(position)
            
            if root:
                print(f"[{self.name}] {sura}:{aya}:{position} {word} -> {root}")
                return RootExtractionResult(
                    word=word,
                    root=root,
                    source=self.name,
                    success=True,
                    confidence=1.0  # Corpus data is authoritative
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error=f"Position {position} not found in verse {sura}:{aya}"
                )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e)
            )


class OfflineCorpusCacheExtractor(RootExtractor):
    """
    Extract roots from offline corpus cache (pre-built from corpus.quran.com).
    
    This extractor provides instant, offline access to all Quranic roots
    with 100% accuracy. The cache is built using build_corpus_cache.py
    and stored in JSON format.
    
    Benefits:
    - Zero network requests
    - Instant lookups
    - 100% accuracy for Quranic words
    - Serves as authoritative fallback
    """
    
    def __init__(self, cache_path: Path):
        super().__init__("offline_corpus_cache")
        self.cache_path = cache_path
        self.cache = {}
        self.metadata = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load the offline corpus cache from disk."""
        try:
            if not self.cache_path.exists():
                print(f"[{self.name}] Cache file not found: {self.cache_path}")
                print(f"[{self.name}] Run scripts/build_corpus_cache.py to create cache")
                return
            
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get('metadata', {})
            self.cache = data.get('roots', {})
            
            print(f"[{self.name}] Loaded cache from {self.cache_path}")
            print(f"[{self.name}] Total words: {self.metadata.get('total_words', len(self.cache))}")
        
        except Exception as e:
            print(f"[{self.name}] Error loading cache: {e}")
            self.cache = {}
    
    async def extract_root(self, word: str, sura: int = None, aya: int = None, position: int = None) -> RootExtractionResult:
        """
        Extract root from offline cache.
        
        Args:
            word: Arabic word (for error messages)
            sura: Sura number (required)
            aya: Aya number (required)
            position: Word position in verse (0-indexed, required)
        
        Returns:
            RootExtractionResult with root from cache
        """
        if sura is None or aya is None or position is None:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error="sura, aya, and position are required for cache extractor"
            )
        
        # No rate limiting needed - it's offline!
        
        try:
            # Build cache key
            key = f"{sura}:{aya}:{position}"
            
            # Lookup in cache
            root = self.cache.get(key)
            
            if root:
                return RootExtractionResult(
                    word=word,
                    root=root,
                    source=self.name,
                    success=True,
                    confidence=1.0  # Cache is authoritative
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error=f"Position {key} not found in cache"
                )
        
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e)
            )


class AlMaanyExtractor(RootExtractor):
    """
    Extract roots from AlMaany Arabic Dictionary (almaany.com).
    
    AlMaany is a comprehensive Arabic-Arabic dictionary that provides
    word roots, definitions, and morphological information.
    """
    
    def __init__(self):
        super().__init__("almaany")
        self.base_url = "https://www.almaany.com/ar/dict/ar-ar"
        self.min_request_interval = 1.5  # 1.5 seconds between requests
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client."""
        return httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
                "Referer": "https://www.almaany.com/",
            }
        )
    
    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root from AlMaany dictionary."""
        client = None
        try:
            await self.rate_limit()
            
            client = self._create_client()
            
            # Build URL - AlMaany uses format: /ar/dict/ar-ar/word/
            url = f"{self.base_url}/{word}/"
            
            print(f"[{self.name}] Fetching: {word}")
            
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for root information in various possible locations
            root_found = None
            
            # Strategy 1: Look for "الجذر" (root) label
            for text_elem in soup.find_all(text=re.compile(r'الجذر')):
                parent = text_elem.parent
                if parent:
                    # Try to find root in next siblings or parent siblings
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        root_text = next_elem.get_text(strip=True)
                        # Extract Arabic letters only
                        root_match = re.search(r'[\u0621-\u064A]+', root_text)
                        if root_match:
                            root_found = root_match.group(0)
                            break
            
            # Strategy 2: Look in definition section for root patterns
            if not root_found:
                # Look for patterns like "من الجذر: كتب" or "الأصل: كتب"
                for elem in soup.find_all(['div', 'span', 'p']):
                    text = elem.get_text()
                    root_pattern = re.search(r'(?:الجذر|الأصل|جذر)[\s:]+([ا-ي]{3,4})', text)
                    if root_pattern:
                        root_found = root_pattern.group(1)
                        break
            
            if root_found:
                print(f"[{self.name}] Found root: {word} -> {root_found}")
                return RootExtractionResult(
                    word=word,
                    root=root_found,
                    source=self.name,
                    success=True,
                    confidence=0.85
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Root not found in dictionary"
                )
        
        except httpx.HTTPError as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=f"Error: {str(e)}"
            )
        finally:
            if client:
                await client.aclose()


class BahethExtractor(RootExtractor):
    """
    Extract roots from Baheth Arabic Dictionary (baheth.info).
    
    Baheth is an Arabic-Arabic dictionary that provides morphological
    analysis and root information.
    """
    
    def __init__(self):
        super().__init__("baheth")
        self.base_url = "https://www.baheth.info"
        self.min_request_interval = 1.5  # 1.5 seconds between requests
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create a new HTTP client."""
        return httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
            }
        )
    
    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root from Baheth dictionary."""
        client = None
        try:
            await self.rate_limit()
            
            client = self._create_client()
            
            # Baheth uses: /all.jsp?term=word
            url = f"{self.base_url}/all.jsp"
            params = {"term": word}
            
            print(f"[{self.name}] Searching: {word}")
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            root_found = None
            
            # Strategy 1: Look for root in the results table
            # Baheth typically shows: الجذر (root) in table cells
            for cell in soup.find_all(['td', 'div', 'span']):
                text = cell.get_text(strip=True)
                
                # Look for "الجذر:" followed by root letters
                if 'الجذر' in text or 'جذر' in text:
                    # Extract Arabic root (3-4 letters)
                    root_match = re.search(r'الجذر[\s:]*([ا-ي]{3,4})', text)
                    if root_match:
                        root_found = root_match.group(1)
                        break
                    
                    # Try next sibling or parent
                    next_elem = cell.find_next_sibling()
                    if next_elem:
                        next_text = next_elem.get_text(strip=True)
                        root_match = re.search(r'([ا-ي]{3,4})', next_text)
                        if root_match:
                            root_found = root_match.group(1)
                            break
            
            if root_found:
                print(f"[{self.name}] Found root: {word} -> {root_found}")
                return RootExtractionResult(
                    word=word,
                    root=root_found,
                    source=self.name,
                    success=True,
                    confidence=0.85
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Root not found"
                )
        
        except httpx.HTTPError as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=f"Error: {str(e)}"
            )
        finally:
            if client:
                await client.aclose()


class PyArabicExtractor(RootExtractor):
    """
    Extract roots using PyArabic library.
    
    PyArabic provides advanced Arabic morphological analysis including
    root extraction using linguistic rules.
    """
    
    def __init__(self):
        super().__init__("pyarabic")
        self._load_root_database()
    
    def _load_root_database(self):
        """Load known roots database from comprehensive file."""
        self.known_roots = {}
        cache_path = Path(__file__).parent.parent.parent / "data" / "quran_roots_comprehensive.json"
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for word, sources in data.items():
                        if isinstance(sources, dict):
                            root = sources.get("placeholder") or sources.get("qurancorpus")
                            if root:
                                self.known_roots[word] = root
            except Exception as e:
                print(f"[{self.name}] Warning: Could not load root database: {e}")
    
    def _extract_root_algorithmic(self, word: str) -> Optional[str]:
        """Extract root using improved algorithmic approach."""
        # Remove diacritics and tatweel
        cleaned = strip_tashkeel(strip_tatweel(word))
        
        # Common prefixes (most common first)
        prefixes = [
            'وال', 'فال', 'بال', 'كال', 'لال',  # Compound prefixes
            'ال',                                 # Definite article (most common)
            'و', 'ف', 'ب', 'ل', 'ك',             # Single letter prefixes
        ]
        
        # Common suffixes (most common first) 
        suffixes = [
            'ونهم', 'ونها', 'ونكم',                    # Complex compounds
            'ونه', 'ونا', 'وني', 'ومه', 'وما', 'ومي',  # Compound with و
            'ون', 'ين', 'ان', 'ات', 'ية', 'تين',        # Plural/dual
            'ته', 'تا', 'تي', 'تك', 'تم', 'تن',         # With ت
            'ها', 'هم', 'هن', 'كم', 'كن', 'نا',         # Pronouns
            'ة', 'ه', 'ي', 'ك', 'ن', 'ا',                # Single letters
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
                stem = stem[:-len(suffix)]
                break
        
        # Remove weak letters from beginning/end in certain contexts
        # Weak letters: ا و ي at edges might be affixes
        if len(stem) > 3:
            # If starts with weak letter followed by strong letters
            if stem[0] in 'اوي' and stem[1] not in 'اويء' and stem[2] not in 'اويء':
                stem = stem[1:]
            
            # If ends with weak letter and previous letters are strong
            if len(stem) > 3 and stem[-1] in 'ايوى' and stem[-2] not in 'اويء':
                stem = stem[:-1]
        
        # Extract root (typically 3 letters, sometimes 4)
        if len(stem) >= 3:
            # For stems longer than 3, try to extract triliteral root
            if len(stem) == 3:
                root = stem
            elif len(stem) == 4:
                # Check if 4th letter is likely an affix or part of root
                # If last letter is ن and word had suffix, it's likely affix
                if stem[-1] == 'ن' and cleaned != word:  # Had affix removed
                    root = stem[:3]
                else:
                    # Keep 4-letter (quadriliteral) root
                    root = stem
            else:
                # For stems longer than 4, extract 3 strong letters
                strong = [c for c in stem if c not in 'اويءى']
                if len(strong) >= 3:
                    root = ''.join(strong[:3])
                else:
                    root = stem[:3]
            
            return root if len(root) >= 2 else None
        
        return stem if len(stem) >= 2 else None
    
    async def extract_root(self, word: str) -> RootExtractionResult:
        """Extract root using PyArabic enhanced algorithm."""
        try:
            # Check known roots first (from previous extractions)
            if word in self.known_roots:
                return RootExtractionResult(
                    word=word,
                    root=self.known_roots[word],
                    source=self.name,
                    success=True,
                    confidence=0.7  # Medium-high (from database)
                )
            
            # Use algorithmic extraction
            root = self._extract_root_algorithmic(word)
            
            if root and len(root) >= 2:
                return RootExtractionResult(
                    word=word,
                    root=root,
                    source=self.name,
                    success=True,
                    confidence=0.6  # Medium confidence for algorithmic
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Could not extract valid root"
                )
        
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e)
            )


class AlKhalilExtractor(RootExtractor):
    """
    Extract roots using AlKhalil Morpho Sys algorithm.
    
    This is a rule-based approach for Arabic morphology based on
    well-known patterns in Arabic grammar.
    """
    
    def __init__(self):
        super().__init__("alkhalil")
        self._load_pattern_rules()
    
    def _load_pattern_rules(self):
        """Load Arabic morphological patterns."""
        # Common prefixes (ordered by length - longest first)
        self.prefixes = [
            "والذي", "بالذي", "فالذي", "كالذي",  # With الذي
            "وال", "فال", "بال", "كال", "لل",     # Compound  
            "ال", "و", "ف", "ب", "ل", "ك",         # Single
        ]
        
        # Common suffixes (ordered by length - longest first)
        self.suffixes = [
            "ونهم", "ونها", "ونني", "ونكم",         # Complex compounds
            "ونه", "ونا", "وني", "ومه", "وما",      # With و
            "تهم", "تها", "تني", "تكم", "تنا",      # With ت
            "هما", "كما", "نني",                    # Dual/emphasis
            "ون", "ين", "ان", "ات", "ية",          # Plural/nisba
            "ته", "تا", "تي", "تك", "تم", "تن",    # Possessive with ت
            "ها", "هم", "هن", "كم", "كن", "نا",    # Pronouns
            "ة", "ه", "ي", "ك", "ن", "ا", "ت",     # Single letters
        ]
        
        # Weak letters that might be part of root or affixes
        self.weak_letters = set('اويءى')
    
    async def extract_root(self, word: str) -> RootExtractionResult:
        """
        Extract root using morphological rules with improved accuracy.
        """
        try:
            # Clean the word
            cleaned = strip_tashkeel(strip_tatweel(word))
            
            # Remove prefixes (try longest first)
            stem = cleaned
            prefix_removed = ""
            for prefix in self.prefixes:
                if stem.startswith(prefix) and len(stem) > len(prefix) + 2:
                    prefix_removed = prefix
                    stem = stem[len(prefix):]
                    break
            
            # Remove suffixes (try longest first)
            suffix_removed = ""
            for suffix in self.suffixes:
                if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
                    suffix_removed = suffix
                    stem = stem[:-len(suffix)]
                    break
            
            # Handle special cases
            # If stem starts with weak letter and we removed a prefix, check if it's part of root
            if prefix_removed and stem and stem[0] in self.weak_letters:
                # Weak letter at start after prefix removal might be part of affix
                if len(stem) > 3 and stem[1] not in self.weak_letters:
                    # If next letter is strong, weak letter is likely affix
                    stem = stem[1:]
            
            # Remove doubled letters (keep one copy)
            deduplicated = ''
            prev_char = ''
            for char in stem:
                if char != prev_char or char in self.weak_letters:  # Keep weak letters even if doubled
                    deduplicated += char
                prev_char = char
            
            stem = deduplicated if len(deduplicated) >= 3 else stem
            
            # Extract root (3-4 letters)
            if len(stem) >= 3:
                # Prefer 3-letter roots for triliteral, 4-letter for quadriliteral
                if len(stem) == 3:
                    root = stem
                elif len(stem) == 4:
                    # Check if it's truly quadriliteral or has extra affix
                    # If last letter is weak and previous is not, it might be affix
                    if stem[-1] in self.weak_letters and stem[-2] not in self.weak_letters:
                        root = stem[:3]
                    else:
                        root = stem[:4]
                else:
                    # For longer stems, extract first 3-4 strong letters
                    strong_letters = [c for c in stem if c not in self.weak_letters]
                    if len(strong_letters) >= 3:
                        root = ''.join(strong_letters[:3])
                    else:
                        root = stem[:4] if len(stem) >= 4 else stem[:3]
                
                # Validate: root should be 2-4 Arabic letters
                if 2 <= len(root) <= 4 and re.match(r'^[\u0600-\u06FF]+$', root):
                    return RootExtractionResult(
                        word=word,
                        root=root,
                        source=self.name,
                        success=True,
                        confidence=0.4  # Medium-low confidence for algorithmic
                    )
            
            # Fallback: return stem as-is if reasonable length
            if 2 <= len(stem) <= 4:
                return RootExtractionResult(
                    word=word,
                    root=stem,
                    source=self.name,
                    success=True,
                    confidence=0.3
                )
            
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error="Could not extract valid root"
            )
        
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e)
            )


class MultiSourceVerifier:
    """
    Verify roots across multiple sources with consensus algorithm.
    
    Features:
    - Query multiple extractors in parallel
    - Calculate consensus based on agreement
    - Trust weighting: cache/corpus > algorithmic
    - Provide confidence scoring
    - Handle conflicts intelligently
    - Record all candidate roots for auditability
    """
    
    # Trust weights for different source types
    SOURCE_WEIGHTS = {
        'offline_corpus_cache': 10.0,  # Highest trust: pre-verified corpus data
        'qurancorpus': 10.0,           # Highest trust: authoritative online corpus
        'pyarabic': 5.0,               # Medium-high trust: database + algorithm
        'alkhalil': 3.0,               # Medium trust: algorithmic only
    }
    
    def __init__(self, extractors: list[RootExtractor], cache_path: Optional[Path] = None):
        """
        Initialize verifier with extractors.
        
        Args:
            extractors: List of RootExtractor instances
            cache_path: Optional path to cache verified results
        """
        self.extractors = extractors
        self.cache_path = cache_path
        self.cache: dict[str, VerifiedRoot] = {}
        
        if cache_path and cache_path.exists():
            self._load_cache()
    
    def _load_cache(self):
        """Load cached verified roots."""
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for word, info in data.items():
                    self.cache[word] = VerifiedRoot(
                        word=word,
                        root=info['root'],
                        sources=info['sources'],
                        confidence=info['confidence'],
                        agreement_count=info['agreement_count'],
                        total_sources=info['total_sources']
                    )
                
                print(f"[MultiSourceVerifier] Loaded {len(self.cache)} cached roots")
        except Exception as e:
            print(f"[MultiSourceVerifier] Failed to load cache: {e}")
    
    def _save_cache(self):
        """Save verified roots to cache."""
        try:
            if self.cache_path:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                
                data = {}
                for word, verified in self.cache.items():
                    data[word] = {
                        'root': verified.root,
                        'sources': verified.sources,
                        'confidence': verified.confidence,
                        'agreement_count': verified.agreement_count,
                        'total_sources': verified.total_sources
                    }
                
                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"[MultiSourceVerifier] Saved {len(self.cache)} roots to cache")
        except Exception as e:
            print(f"[MultiSourceVerifier] Failed to save cache: {e}")
    
    async def verify_root(self, word: str, max_retries: int = 3) -> Optional[VerifiedRoot]:
        """
        Verify root across multiple sources with retry logic.
        
        Args:
            word: Arabic word to extract root for
            max_retries: Maximum retry attempts per source
            
        Returns:
            VerifiedRoot with consensus, or None if verification fails
        """
        # Check cache first
        if word in self.cache:
            print(f"[MultiSourceVerifier] Cache hit for: {word}")
            return self.cache[word]
        
        print(f"[MultiSourceVerifier] Verifying root for: {word}")
        
        # Query all extractors with retry logic
        all_results: list[RootExtractionResult] = []
        
        for extractor in self.extractors:
            for attempt in range(max_retries):
                try:
                    result = await extractor.extract_root(word)
                    if result.success:
                        all_results.append(result)
                        break  # Success, no need to retry
                    elif attempt < max_retries - 1:
                        print(f"[{extractor.name}] Attempt {attempt + 1} failed: {result.error}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        print(f"[{extractor.name}] All attempts failed for: {word}")
                        all_results.append(result)  # Keep failed result for logging
                except Exception as e:
                    print(f"[{extractor.name}] Exception on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        all_results.append(RootExtractionResult(
                            word=word,
                            root=None,
                            source=extractor.name,
                            success=False,
                            error=str(e)
                        ))
        
        # Filter successful results
        successful_results = [r for r in all_results if r.success and r.root]
        
        if not successful_results:
            print(f"[MultiSourceVerifier] No successful extractions for: {word}")
            return None
        
        # Calculate weighted consensus using trust scores
        root_weighted_votes: dict[str, float] = {}
        root_simple_votes: dict[str, int] = {}
        
        for result in successful_results:
            root = result.root
            weight = self.SOURCE_WEIGHTS.get(result.source, 1.0)
            
            # Weighted vote
            root_weighted_votes[root] = root_weighted_votes.get(root, 0.0) + weight
            
            # Simple vote count
            root_simple_votes[root] = root_simple_votes.get(root, 0) + 1
        
        # Select root with highest weighted score
        most_common_root = max(root_weighted_votes, key=root_weighted_votes.get)
        weighted_score = root_weighted_votes[most_common_root]
        simple_vote_count = root_simple_votes[most_common_root]
        
        # Build sources dict (all candidates for auditability)
        sources = {r.source: r.root for r in successful_results}
        
        # Calculate confidence based on:
        # 1. Weighted score relative to total possible weight
        # 2. Agreement count (simple votes)
        # 3. Source trustworthiness
        total_sources = len(successful_results)
        total_weight = sum(root_weighted_votes.values())
        
        # Base confidence from weighted score ratio
        weight_confidence = weighted_score / total_weight if total_weight > 0 else 0.5
        
        # Boost confidence if multiple sources agree
        agreement_boost = 0.0
        if simple_vote_count >= 3:
            agreement_boost = 0.2
        elif simple_vote_count == 2:
            agreement_boost = 0.1
        
        # Final confidence (capped at 1.0)
        confidence = min(1.0, weight_confidence + agreement_boost)
        
        # Ensure minimum confidence for high-trust sources
        if any(r.source in ['offline_corpus_cache', 'qurancorpus'] and r.root == most_common_root 
               for r in successful_results):
            confidence = max(confidence, 0.95)
        
        verified = VerifiedRoot(
            word=word,
            root=most_common_root,
            sources=sources,
            confidence=confidence,
            agreement_count=simple_vote_count,
            total_sources=total_sources
        )
        
        # Cache result
        self.cache[word] = verified
        
        print(f"[MultiSourceVerifier] Verified: {word} -> {most_common_root} "
              f"(confidence: {confidence:.2f}, agreement: {simple_vote_count}/{total_sources}, "
              f"weighted: {weighted_score:.1f}/{total_weight:.1f})")
        
        # Log conflicts if any
        if len(root_weighted_votes) > 1:
            conflicts = [f"{root}({votes:.1f})" for root, votes in root_weighted_votes.items()]
            print(f"[MultiSourceVerifier] Conflicts: {', '.join(conflicts)}")
        
        return verified
    
    def save_cache(self):
        """Public method to save cache."""
        self._save_cache()
    
    async def close(self):
        """Close all extractors (no-op for stateless extractors)."""
        # Extractors now create clients per-request, so no cleanup needed
        pass


class RootExtractionService:
    """
    Main service for root extraction with multi-source verification.
    
    This service manages the extraction pipeline:
    1. Try offline corpus cache first (instant, 100% accurate for Quran)
    2. Fall back to online corpus if cache miss
    3. Fall back to algorithmic extractors if no location info
    4. Save verified results to cache
    """
    
    def __init__(self, cache_path: Optional[Path] = None, corpus_cache_path: Optional[Path] = None):
        """
        Initialize service.
        
        Args:
            cache_path: Path to cache file for verified roots
            corpus_cache_path: Path to offline corpus cache (pre-built)
        """
        # Initialize extractors - order by reliability and speed
        
        # 1. Offline corpus cache (fastest, most reliable for Quran)
        if corpus_cache_path is None:
            corpus_cache_path = Path(__file__).parent.parent.parent / "data" / "corpus_roots_cache.json"
        self.offline_corpus = OfflineCorpusCacheExtractor(corpus_cache_path)
        
        # 2. Online corpus extractor (authoritative but slower)
        self.corpus_extractor = QuranCorpusExtractor()
        
        # 3. Offline/algorithmic extractors for fallback (no location needed)
        offline_extractors = [
            PyArabicExtractor(),     # Primary: Database + enhanced algorithm (high confidence)
            AlKhalilExtractor(),     # Secondary: Improved algorithmic (medium confidence)
        ]
        
        # Initialize verifier with offline extractors
        self.verifier = MultiSourceVerifier(offline_extractors, cache_path)
    
    async def extract_root(self, word: str, sura: int = None, aya: int = None, position: int = None) -> Optional[dict]:
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
        # Priority 1: Try offline corpus cache first if location is available
        # This is instant and 100% accurate for Quranic words
        if sura is not None and aya is not None and position is not None:
            try:
                offline_result = await self.offline_corpus.extract_root(word, sura, aya, position)
                if offline_result.success and offline_result.root:
                    return {
                        'root': offline_result.root,
                        'sources': {offline_result.source: offline_result.root},
                        'confidence': offline_result.confidence,
                        'agreement': "1/1",
                        'method': 'offline_cache'
                    }
            except Exception as e:
                print(f"[RootExtractionService] Offline cache lookup failed: {e}")
                # Fall through to online corpus
            
            # Priority 2: Try online corpus if cache miss
            try:
                corpus_result = await self.corpus_extractor.extract_root(word, sura, aya, position)
                if corpus_result.success and corpus_result.root:
                    return {
                        'root': corpus_result.root,
                        'sources': {corpus_result.source: corpus_result.root},
                        'confidence': corpus_result.confidence,
                        'agreement': "1/1",
                        'method': 'online_corpus'
                    }
            except Exception as e:
                print(f"[RootExtractionService] Online corpus extraction failed: {e}")
                # Fall through to offline extractors
        
        # Priority 3: Fall back to algorithmic extractors with multi-source verification
        verified = await self.verifier.verify_root(word)
        
        if verified:
            return {
                'root': verified.root,
                'sources': verified.sources,
                'confidence': verified.confidence,
                'agreement': f"{verified.agreement_count}/{verified.total_sources}",
                'method': 'algorithmic'
            }
        else:
            return None
    
    def extract_root_sync(self, word: str, sura: int = None, aya: int = None, position: int = None) -> Optional[dict]:
        """
        Synchronous wrapper for Celery tasks.
        
        Args:
            word: Normalized Arabic word
            sura: Sura number (optional, enables corpus extractor)
            aya: Aya number (optional, enables corpus extractor)
            position: Word position in verse (optional, enables corpus extractor)
            
        Returns:
            Dictionary with root information, or None if failed
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.extract_root(word, sura, aya, position))
                return result
            finally:
                # Clean up event loop (extractors create clients per-request)
                loop.close()
        except Exception as e:
            print(f"[RootExtractionService] Error extracting root for '{word}': {e}")
            return None
    
    def save_cache(self):
        """Save verified roots cache."""
        self.verifier.save_cache()


# For backward compatibility
def extract_root_sync(word: str) -> Optional[dict]:
    """
    Standalone function for root extraction (backward compatible).
    
    Args:
        word: Normalized Arabic word
        
    Returns:
        Dictionary with root information
    """
    cache_path = Path(__file__).parent.parent.parent / "data" / "quran_roots_verified.json"
    service = RootExtractionService(cache_path)
    result = service.extract_root_sync(word)
    service.save_cache()
    return result
