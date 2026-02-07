#!/usr/bin/env python3
"""
Extract roots from corpus.quran.com word-by-word page
"""
import httpx
import re
from bs4 import BeautifulSoup

def fetch_roots_from_verse(sura: int, verse: int) -> dict:
    """
    Fetch all roots from a verse from corpus.quran.com
    
    Returns dict: {word: root}
    """
    try:
        url = f"https://corpus.quran.com/wordbyword.jsp?chapter={sura}&verse={verse}"
        
        print(f"[Corpus] Fetching sura {sura} verse {verse}...")
        
        client = httpx.Client(timeout=30, follow_redirects=True)
        response = client.get(url)
        response.raise_for_status()
        client.close()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all morphology table rows
        results = {}
        
        # Each row has: translation | arabic word image | morphology
        # The translation cell contains <a href="/qurandictionary.jsp?q=ROOT#(1:1:1)">phonetic</a>
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                # First cell has the dictionary link
                translation_cell = cells[0]
                dict_link = translation_cell.find('a', href=re.compile(r'/qurandictionary\.jsp\?q='))
                
                if dict_link:
                    # Extract root from URL: /qurandictionary.jsp?q=smw#(1:1:1)
                    href = dict_link.get('href', '')
                    match = re.search(r'q=([a-zA-Z]+)', href)
                    if match:
                        root_latin = match.group(1)
                        
                        # Get the phonetic/transliterated word
                        phonetic = dict_link.text.strip()
                        
                        # Get location
                        location_span = translation_cell.find('span', class_='location')
                        location = location_span.text.strip() if location_span else 'unknown'
                        
                        print(f"  {location}: {phonetic} -> root: {root_latin}")
                        results[phonetic] = root_latin
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        return {}


# Map of Latin letters to Arabic root letters (approximation)
LATIN_TO_ARABIC_ROOTS = {
    'smw': 'سمو',  # name
    'Alh': 'اله',  # Allah
    'rHm': 'رحم',  # mercy
    'Hmd': 'حمد',  # praise
    'rbb': 'ربب',  # lord
    'Elm': 'علم',  # world/knowledge
    'mlk': 'ملك',  # king/owner
    'ywm': 'يوم',  # day
    'dyn': 'دين',  # religion/judgment
    'Ebd': 'عبد',  # worship
    'Ewn': 'عون',  # help
    'hdy': 'هدي',  # guidance
    'SrT': 'صرط',  # path
    'qwm': 'قوم',  # straight/establish
}


if __name__ == "__main__":
    print("="*70)
    print("Testing Corpus Quran Root Extraction")
    print("="*70)
    
    # Test with Sura 1 (Al-Fatiha), verses 1-3
    roots = fetch_roots_from_verse(1, 1)
    
    print("\n" + "="*70)
    print(f"Found {len(roots)} word-root mappings")
    print("="*70)
    
    # Show Arabic equivalents if we have them
    for word, root_latin in roots.items():
        arabic_root = LATIN_TO_ARABIC_ROOTS.get(root_latin, '?')
        print(f"{word:15} -> {root_latin:6} ({arabic_root})")
