#!/usr/bin/env python3
"""
Test extracting Arabic root from corpus.quran.com dictionary page
"""
import httpx
import re
from bs4 import BeautifulSoup

def get_arabic_root_from_corpus(latin_root: str) -> str | None:
    """
    Get Arabic root from corpus.quran.com dictionary page
    
    Args:
        latin_root: Latin transliteration (e.g., 'smw', 'rHm')
        
    Returns:
        Arabic root or None
    """
    try:
        url = f"https://corpus.quran.com/qurandictionary.jsp?q={latin_root}"
        
        print(f"[Corpus] Fetching root for: {latin_root}")
        
        client = httpx.Client(timeout=30, follow_redirects=True)
        response = client.get(url)
        response.raise_for_status()
        client.close()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save for inspection
        with open(f'debug_corpus_dict_{latin_root}.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        
        # Look for the root in Arabic
        # The page has sections with Arabic roots
        
        # Strategy 1: Find element with class containing "root" or Arabic text
        for elem in soup.find_all(['span', 'div', 'td', 'h3', 'b']):
            text = elem.get_text().strip()
            # Check if contains Arabic letters
            if re.search(r'[ا-ي]{2,4}', text):
                # If short (2-4 chars), likely a root
                clean_text = re.sub(r'[^ا-ي]', '', text)
                if 2 <= len(clean_text) <= 4:
                    print(f"  Found potential root: {clean_text}")
                    return clean_text
        
        return None
        
    except Exception as e:
        print(f"  Error: {e}")
        return None


if __name__ == "__main__":
    print("="*70)
    print("Testing Corpus Dictionary Root Extraction")
    print("="*70)
    
    test_roots = ['smw', 'rHm', 'Alh', 'Hmd', 'ktb']
    
    for latin in test_roots:
        print(f"\n{latin}:")
        arabic = get_arabic_root_from_corpus(latin)
        if arabic:
            print(f"  ✓ Arabic root: {arabic}")
        else:
            print(f"  ✗ Not found")
