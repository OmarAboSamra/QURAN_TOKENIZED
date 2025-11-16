"""Build comprehensive root dictionary for Sura 1 and 2 from Quranic Arabic Corpus."""
import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_sync_session_maker
from backend.models import Token


class QuranCorpusAPI:
    """Fetch morphological data from Quranic Arabic Corpus."""
    
    BASE_URL = "https://corpus.quran.com"
    
    def __init__(self):
        self.session = None
        self.roots_cache = {}
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def fetch_verse_morphology(self, sura: int, aya: int) -> dict:
        """Fetch morphological analysis for a specific verse."""
        try:
            url = f"{self.BASE_URL}/wordbyword.jsp?chapter={sura}&verse={aya}"
            print(f"  Fetching Sura {sura}:{aya}... ", end="", flush=True)
            
            response = await self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            verse_data = {}
            
            # Find all word segments
            segments = soup.find_all('td', class_='graphCell')
            
            for segment in segments:
                # Extract Arabic text
                arabic_div = segment.find('div', class_='arabic')
                if not arabic_div:
                    continue
                    
                arabic_text = arabic_div.get_text(strip=True)
                
                # Find morphology link
                morph_link = segment.find('a', href=re.compile(r'wordmorphology\.jsp'))
                if not morph_link:
                    continue
                
                # Extract root from morphology page
                morph_href = morph_link['href']
                root = await self._extract_root_from_morphology(morph_href)
                
                if root:
                    # Normalize the Arabic text (remove diacritics)
                    normalized = self._normalize_arabic(arabic_text)
                    verse_data[normalized] = root
            
            print(f"[OK] Found {len(verse_data)} words with roots")
            return verse_data
            
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            return {}
    
    async def _extract_root_from_morphology(self, href: str) -> str:
        """Extract root from morphology page."""
        try:
            # Check cache first
            if href in self.roots_cache:
                return self.roots_cache[href]
            
            full_url = f"{self.BASE_URL}/{href}" if not href.startswith('http') else href
            response = await self.session.get(full_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for root information in the morphology table
            # Pattern: ROOT: <arabic root>
            root_row = soup.find('td', string=re.compile(r'ROOT', re.IGNORECASE))
            if root_row:
                root_cell = root_row.find_next_sibling('td')
                if root_cell:
                    root_text = root_cell.get_text(strip=True)
                    # Clean up the root (remove parentheses, extra info)
                    root = re.sub(r'\s*\([^)]*\)\s*', '', root_text).strip()
                    self.roots_cache[href] = root
                    return root
            
            return None
            
        except Exception as e:
            return None
    
    def _normalize_arabic(self, text: str) -> str:
        """Remove diacritics from Arabic text."""
        # Arabic diacritics unicode ranges
        diacritics = re.compile(r'[\u064B-\u065F\u0670]')
        return diacritics.sub('', text).strip()


async def build_roots_dictionary():
    """Build comprehensive roots dictionary for Sura 1 and 2."""
    print("=" * 70)
    print("  Building Comprehensive Roots Dictionary")
    print("=" * 70)
    print()
    
    # Get all verses from database
    print("[1/4] Loading verses from database...")
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    verses_to_fetch = []
    for sura in [1, 2]:
        verse_numbers = session.query(Token.aya).filter(
            Token.sura == sura
        ).distinct().all()
        
        for (aya,) in verse_numbers:
            verses_to_fetch.append((sura, aya))
    
    print(f"  Found {len(verses_to_fetch)} verses to process")
    print()
    
    # Fetch morphology from Quranic Arabic Corpus
    print("[2/4] Fetching morphology data from corpus.quran.com...")
    all_roots = {}
    
    async with QuranCorpusAPI() as api:
        for sura, aya in verses_to_fetch:
            verse_roots = await api.fetch_verse_morphology(sura, aya)
            all_roots.update(verse_roots)
            
            # Rate limiting - be nice to the server
            await asyncio.sleep(0.5)
    
    print()
    print(f"  [OK] Collected roots for {len(all_roots)} unique words")
    print()
    
    # Save to cache file
    print("[3/4] Saving to cache file...")
    cache_path = Path("data/quran_roots_comprehensive.json")
    
    # Convert to format: {word: {"qurancorpus": root}}
    formatted_cache = {
        word: {"qurancorpus": root}
        for word, root in all_roots.items()
    }
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_cache, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Saved to {cache_path}")
    print()
    
    # Summary
    print("[4/4] Summary:")
    print(f"  Total unique words: {len(all_roots)}")
    print(f"  Sura 1 + 2 should have ~2,266 unique words")
    print(f"  Coverage: {len(all_roots)/2266*100:.1f}%")
    print()
    
    # Get database word count
    unique_db_words = session.query(Token.normalized).filter(
        Token.sura.in_([1, 2])
    ).distinct().count()
    
    missing_count = unique_db_words - len(all_roots)
    print(f"  Database has {unique_db_words} unique normalized words")
    print(f"  Missing roots: {missing_count}")
    print()
    
    if missing_count > 0:
        print("  [!] Not all words have roots. Possible reasons:")
        print("      - API structure changed")
        print("      - Network errors during fetch")
        print("      - Normalization mismatch")
        print()
        print("  Run this script again or manually add missing roots to the cache file.")
    else:
        print("  [OK] Complete! All words have roots.")
    
    session.close()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(build_roots_dictionary())
