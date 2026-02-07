#!/usr/bin/env python3
"""
Test corpus.quran.com morphology API for root extraction
"""
import httpx
import json
from pathlib import Path

def fetch_root_from_corpus(word: str) -> tuple[str | None, str | None]:
    """
    Fetch root from Quranic Arabic Corpus morphology API
    
    Args:
        word: Arabic word to look up
        
    Returns:
        tuple: (root, error)
    """
    try:
        # Corpus morphology search API
        url = f"https://corpus.quran.com/morphology.jsp?location=(1:1:1)"
        
        print(f"[Corpus] Fetching morphology data...")
        
        client = httpx.Client(timeout=30, follow_redirects=True)
        response = client.get(url)
        response.raise_for_status()
        
        # Save for inspection
        debug_file = Path(__file__).parent.parent / f'debug_corpus.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"[Debug] Saved to: {debug_file}")
        
        # Try their word-by-word API
        url2 = f"https://corpus.quran.com/wordbyword.jsp?chapter=1&verse=1"
        response2 = client.get(url2)
        
        debug_file2 = Path(__file__).parent.parent / f'debug_corpus_word.html'
        with open(debug_file2, 'w', encoding='utf-8') as f:
            f.write(response2.text)
        print(f"[Debug] Saved to: {debug_file2}")
        
        client.close()
        
        return None, "Check saved HTML files"
        
    except Exception as e:
        return None, f"Error: {str(e)}"


if __name__ == "__main__":
    print("="*70)
    print("Testing Corpus Quran API")
    print("="*70)
    
    result, error = fetch_root_from_corpus("بسم")
    if result:
        print(f"✓ Found root: {result}")
    else:
        print(f"✗ {error}")
