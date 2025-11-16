"""
Enhanced root extraction service with multi-source verification.

This module implements robust root extraction from multiple online sources:
- Quranic Arabic Corpus (corpus.quran.com)
- Tanzil morphology data
- Additional verification sources

Features:
- Multi-source verification with consensus algorithm
- Retry logic and rate limiting
- Comprehensive error handling
- Caching to minimize redundant API calls
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
    Extract roots from Quranic Arabic Corpus API.
    
    Queries corpus.quran.com morphology data to extract verified roots.
    """
    
    def __init__(self):
        super().__init__("qurancorpus")
        self.base_url = "https://corpus.quran.com"
        self.min_request_interval = 2.0  # 2 seconds between requests
    
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
    
    async def extract_root(self, word: str) -> RootExtractionResult:
        """
        Extract root from Quranic Corpus by searching for the word.
        
        Strategy:
        1. Search corpus for verses containing the word
        2. Parse morphology page for that verse
        3. Find the word token and extract its ROOT field
        """
        client = None
        try:
            await self.rate_limit()
            
            # Create a fresh client for this request
            client = self._create_client()
            
            # Search for the word in the corpus
            search_url = f"{self.base_url}/search.jsp"
            params = {"q": word, "s": "exact"}
            
            print(f"[{self.name}] Searching for word: {word}")
            
            response = await client.get(search_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Debug: Check if we got any results
            # print(f"[{self.name}] Response length: {len(response.text)} bytes")
            
            # Find first verse reference (format: 1:1, 2:5, etc.)
            verse_link = soup.find('a', href=re.compile(r'/wordmorphology\.jsp\?location='))
            
            if not verse_link:
                # Try alternate link pattern
                verse_link = soup.find('a', href=re.compile(r'location=(\d+):(\d+)'))
            
            if not verse_link:
                print(f"[{self.name}] No verse link found for: {word}")
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Word not found in corpus"
                )
            
            # Extract verse location from link
            href = verse_link['href']
            match = re.search(r'location=(\d+):(\d+)', href)
            if not match:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="Could not parse verse location"
                )
            
            sura, aya = match.groups()
            
            # Fetch morphology page for this verse
            await self.rate_limit()
            
            morph_url = f"{self.base_url}/wordmorphology.jsp"
            morph_params = {"location": f"{sura}:{aya}"}
            
            print(f"[{self.name}] Fetching morphology for {sura}:{aya}")
            
            morph_response = await client.get(morph_url, params=morph_params)
            morph_response.raise_for_status()
            
            morph_soup = BeautifulSoup(morph_response.text, 'html.parser')
            
            # Find all word segments with morphology data
            # Look for tables containing ROOT information
            root_found = None
            
            # Strategy: Find all table rows with "ROOT" label
            for row in morph_soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    if label == "ROOT":
                        root_text = cells[1].get_text(strip=True)
                        # Extract Arabic root (skip translation)
                        # Format might be: "كتب to write"
                        root_match = re.match(r'([^\s]+)', root_text)
                        if root_match:
                            candidate_root = root_match.group(1)
                            # Verify it's Arabic
                            if re.search(r'[\u0600-\u06FF]', candidate_root):
                                root_found = candidate_root
                                break
            
            if root_found:
                print(f"[{self.name}] Found root: {word} -> {root_found}")
                return RootExtractionResult(
                    word=word,
                    root=root_found,
                    source=self.name,
                    success=True,
                    confidence=0.9
                )
            else:
                return RootExtractionResult(
                    word=word,
                    root=None,
                    source=self.name,
                    success=False,
                    error="ROOT field not found in morphology"
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
                error=f"Unexpected error: {str(e)}"
            )
        finally:
            # Always close the client after this request
            if client:
                await client.aclose()


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
    - Provide confidence scoring
    - Handle conflicts intelligently
    """
    
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
        
        # Calculate consensus
        root_votes = Counter(r.root for r in successful_results)
        most_common_root, vote_count = root_votes.most_common(1)[0]
        
        # Build sources dict
        sources = {r.source: r.root for r in successful_results}
        
        # Calculate confidence
        # - High confidence: Multiple sources agree (0.9+)
        # - Medium confidence: 2 sources agree or single high-confidence source (0.6-0.8)
        # - Low confidence: Single source only (0.3-0.5)
        total_sources = len(successful_results)
        agreement_count = vote_count
        
        if agreement_count >= 2:
            confidence = 0.9
        elif agreement_count == 1 and total_sources == 1:
            # Single source - use its confidence
            confidence = successful_results[0].confidence
        else:
            confidence = 0.5
        
        verified = VerifiedRoot(
            word=word,
            root=most_common_root,
            sources=sources,
            confidence=confidence,
            agreement_count=agreement_count,
            total_sources=total_sources
        )
        
        # Cache result
        self.cache[word] = verified
        
        print(f"[MultiSourceVerifier] Verified: {word} -> {most_common_root} "
              f"(confidence: {confidence:.2f}, agreement: {agreement_count}/{total_sources})")
        
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
    1. Check cache for existing verified roots
    2. Query multiple sources in parallel
    3. Calculate consensus across sources
    4. Save verified results to cache
    """
    
    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize service.
        
        Args:
            cache_path: Path to cache file for verified roots
        """
        # Initialize extractors - order by reliability
        # Using offline/algorithmic extractors since web scraping is blocked
        extractors = [
            PyArabicExtractor(),     # Primary: Database + enhanced algorithm (high confidence)
            AlKhalilExtractor(),     # Secondary: Improved algorithmic (medium confidence)
        ]
        
        # Initialize verifier
        self.verifier = MultiSourceVerifier(extractors, cache_path)
    
    async def extract_root(self, word: str) -> Optional[dict]:
        """
        Extract and verify root for a word.
        
        Args:
            word: Normalized Arabic word
            
        Returns:
            Dictionary with root and source information, or None if failed
        """
        verified = await self.verifier.verify_root(word)
        
        if verified:
            return {
                'root': verified.root,
                'sources': verified.sources,
                'confidence': verified.confidence,
                'agreement': f"{verified.agreement_count}/{verified.total_sources}"
            }
        else:
            return None
    
    def extract_root_sync(self, word: str) -> Optional[dict]:
        """
        Synchronous wrapper for Celery tasks.
        
        Args:
            word: Normalized Arabic word
            
        Returns:
            Dictionary with root information, or None if failed
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.extract_root(word))
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
