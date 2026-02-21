"""
QuranCorpusExtractor — fetches roots from corpus.quran.com.

Scrapes the word-by-word morphological analysis pages and converts
Buckwalter transliteration to Arabic.  Results are cached per-verse
so that a single HTTP request covers all words in a verse.
"""
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from backend.services.extractors.base import RootExtractionResult, RootExtractor


class QuranCorpusExtractor(RootExtractor):
    """
    Extract roots from Quranic Arabic Corpus word-by-word pages.

    Fetches pre-extracted roots from corpus.quran.com which provides accurate
    morphological analysis including roots in Buckwalter transliteration.
    """

    def __init__(self) -> None:
        super().__init__("qurancorpus")
        self.base_url = "https://corpus.quran.com"
        self.min_request_interval = 1.0
        self.verse_cache: dict[str, dict[int, str]] = {}

        # Buckwalter → Arabic transliteration map
        self.buckwalter_map: dict[str, str] = {
            'A': 'ا', 'b': 'ب', 't': 'ت', 'v': 'ث', 'j': 'ج', 'H': 'ح', 'x': 'خ',
            'd': 'د', '*': 'ذ', 'r': 'ر', 'z': 'ز', 's': 'س', '$': 'ش', 'S': 'ص',
            'D': 'ض', 'T': 'ط', 'Z': 'ظ', 'E': 'ع', 'g': 'غ', 'f': 'ف', 'q': 'ق',
            'k': 'ك', 'l': 'ل', 'm': 'م', 'n': 'ن', 'h': 'ه', 'w': 'و', 'y': 'ي',
            'Y': 'ى', "'": 'ء', 'p': 'ة', '|': 'آ', '>': 'أ', '<': 'إ', '&': 'ؤ',
            '}': 'ئ',
        }

    def _buckwalter_to_arabic(self, text: str) -> str:
        """Convert Buckwalter transliteration to Arabic."""
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
            },
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

        client: Optional[httpx.AsyncClient] = None
        try:
            client = self._create_client()
            url = f"{self.base_url}/wordbyword.jsp?chapter={sura}&verse={aya}"

            print(f"[{self.name}] Fetching verse {sura}:{aya}")

            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            roots: dict[int, str] = {}

            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:
                    translation_cell = cells[0]
                    dict_link = translation_cell.find(
                        'a', href=re.compile(r'/qurandictionary\.jsp\?q='),
                    )

                    if dict_link:
                        location_span = translation_cell.find('span', class_='location')
                        if location_span:
                            location_text = location_span.text.strip()
                            loc_match = re.match(r'\((\d+):(\d+):(\d+)\)', location_text)
                            if loc_match:
                                loc_sura, loc_aya, word_index = map(int, loc_match.groups())
                                if loc_sura == sura and loc_aya == aya:
                                    href = dict_link.get('href', '')
                                    root_match = re.search(r'q=([a-zA-Z*$]+)', href)
                                    if root_match:
                                        root_buckwalter = root_match.group(1)
                                        root_arabic = self._buckwalter_to_arabic(root_buckwalter)
                                        position = word_index - 1
                                        roots[position] = root_arabic

            print(f"[{self.name}] Found {len(roots)} words in verse {sura}:{aya}")
            self.verse_cache[cache_key] = roots
            return roots

        except Exception as e:
            print(f"[{self.name}] Error fetching verse {sura}:{aya}: {e}")
            return {}
        finally:
            if client:
                await client.aclose()

    async def extract_root(
        self,
        word: str,
        sura: Optional[int] = None,
        aya: Optional[int] = None,
        position: Optional[int] = None,
        **kwargs,
    ) -> RootExtractionResult:
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
                error="sura, aya, and position are required for corpus extractor",
            )

        try:
            await self.rate_limit()
            verse_roots = await self._fetch_verse_roots(sura, aya)
            root = verse_roots.get(position)

            if root:
                print(f"[{self.name}] {sura}:{aya}:{position} {word} -> {root}")
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
                    error=f"Position {position} not found in verse {sura}:{aya}",
                )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )
