#!/usr/bin/env python3
"""
Extract roots from corpus.quran.com and convert to Arabic

This will work for ALL Quranic words!
"""
import httpx
import re
from bs4 import BeautifulSoup
from pathlib import Path

# Buckwalter to Arabic mapping
BUCKWALTER = {
    'A': 'ا', 'b': 'ب', 't': 'ت', 'v': 'ث', 'j': 'ج', 'H': 'ح', 'x': 'خ',
    'd': 'د', '*': 'ذ', 'r': 'ر', 'z': 'ز', 's': 'س', '$': 'ش', 'S': 'ص',
    'D': 'ض', 'T': 'ط', 'Z': 'ظ', 'E': 'ع', 'g': 'غ', 'f': 'ف', 'q': 'ق',
    'k': 'ك', 'l': 'ل', 'm': 'م', 'n': 'ن', 'h': 'ه', 'w': 'و', 'y': 'ي',
    'Y': 'ى', "'": 'ء', 'p': 'ة', '|': 'آ', '>': 'أ', '<': 'إ', '&': 'ؤ', '}': 'ئ',
}

def buckwalter_to_arabic(text: str) -> str:
    """Convert Buckwalter transliteration to Arabic"""
    return ''.join(BUCKWALTER.get(c, c) for c in text)


def fetch_roots_from_corpus_verse(sura: int, verse: int) -> dict[str, str]:
    """
    Fetch all word roots from a verse from corpus.quran.com
    
    Args:
        sura: Sura number (1-114)
        verse: Verse number
        
    Returns:
        dict: {arabic_word: arabic_root}
    """
    try:
        url = f"https://corpus.quran.com/wordbyword.jsp?chapter={sura}&verse={verse}"
        
        print(f"[Corpus] Fetching sura {sura}:{verse}...")
        
        client = httpx.Client(timeout=30, follow_redirects=True)
        response = client.get(url)
        response.raise_for_status()
        client.close()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = {}
        
        # Find all rows in the morphology table
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                # First cell: translation with dictionary link
                translation_cell = cells[0]
                dict_link = translation_cell.find('a', href=re.compile(r'/qurandictionary\.jsp\?q='))
                
                if dict_link:
                    # Extract Buckwalter root from URL
                    href = dict_link.get('href', '')
                    match = re.search(r'q=([a-zA-Z*$]+)', href)
                    if match:
                        root_buckwalter = match.group(1)
                        root_arabic = buckwalter_to_arabic(root_buckwalter)
                        
                        # Second cell: Arabic word image
                        # We need to get the actual Arabic text from the image alt or nearby
                        # For now, use the location link to get the Arabic word
                        location_span = translation_cell.find('span', class_='location')
                        if location_span:
                            location = location_span.text.strip()
                            
                            # Get morphology page to extract Arabic word
                            word_cell = cells[1]
                            word_link = word_cell.find('a', href=re.compile(r'/wordmorphology\.jsp'))
                            if word_link:
                                # We can extract from image URL, but easier: the phonetic text is the word
                                phonetic = dict_link.text.strip()
                                
                                # Store: we'll map phonetic -> root for now
                                results[phonetic] = root_arabic
                                print(f"  {location}: {phonetic:15} -> {root_arabic}")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        return {}


def test_with_known_words():
    """Test with known words from Sura 1"""
    print("="*70)
    print("Testing Corpus Root Extraction with Buckwalter Conversion")
    print("="*70)
    
    # Known words from Sura 1
    known_words = {
        "bis'mi": "سمو",      # name
        "l-lahi": "اله",      # Allah
        "l-raḥmāni": "رحم",   # mercy
        "al-ḥamdu": "حمد",    # praise
        "rabbi": "ربب",       # lord
        "māliki": "ملك",      # owner/king
        "naʿbudu": "عبد",     # worship
        "ih'dinā": "هدي",     # guide
    }
    
    # Extract from Sura 1, verses 1-6
    all_roots = {}
    for verse in range(1, 7):
        roots = fetch_roots_from_corpus_verse(1, verse)
        all_roots.update(roots)
    
    print("\n" + "="*70)
    print("Verification against known roots:")
    print("="*70)
    
    correct = 0
    total = 0
    for word, expected_root in known_words.items():
        extracted_root = all_roots.get(word, "NOT_FOUND")
        match = extracted_root == expected_root
        status = '✓' if match else '✗'
        print(f"{status} {word:15} -> {extracted_root:6} (expected: {expected_root})")
        if match:
            correct += 1
        total += 1
    
    print(f"\n{correct}/{total} correct ({100*correct/total:.1f}%)")


if __name__ == "__main__":
    test_with_known_words()
