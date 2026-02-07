"""
AlMaany Quran Root Extractor with Cloudflare bypass.
"""

import asyncio
import re
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import cloudscraper
from bs4 import BeautifulSoup


def fetch_root_from_almaany_sync(word: str) -> tuple[str, str]:
    """
    Fetch root for a word from AlMaany Quran section (synchronous).
    
    Returns:
        tuple: (root, error) - root if found, else None with error message
    """
    # Create scraper that can bypass Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    try:
        # Search URL - POST form submission
        search_url = "https://www.almaany.com/quran-b/"
        
        print(f"[AlMaany] Searching for: {word}")
        
        # Submit search form with word
        form_data = {
            'service': 'quran-b',
            'language': 'arabic',
            'word': word,
            'srchtype': '1',  # 1 = search by root, 0 = search by stem
        }
        
        response = scraper.post(search_url, data=form_data, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Save HTML to file for inspection
        debug_file = Path(__file__).parent.parent / f'debug_{word}.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"[Debug] Saved HTML to: {debug_file}")
        
        # Strategy 1: Look for root in specific AlMaany structure
        # AlMaany shows results in a table or div structure
        
        # Look for any element containing root information
        root_found = None
        
        # Search for "الجذر" text
        for elem in soup.find_all(text=re.compile(r'الجذر|جذر')):
            parent = elem.find_parent()
            if parent:
                # Try to find the root value nearby
                siblings = list(parent.next_siblings)
                for sibling in siblings[:3]:  # Check next 3 siblings
                    if sibling and hasattr(sibling, 'get_text'):
                        text = sibling.get_text(strip=True)
                        # Extract Arabic root (2-4 letters)
                        root_match = re.search(r'^([ا-ي]{2,4})$', text)
                        if root_match:
                            root_found = root_match.group(1)
                            break
                if root_found:
                    break
        
        # Strategy 2: Look in the word analysis section
        if not root_found:
            # Find elements with class or id related to root
            for elem in soup.find_all(['span', 'div', 'td'], class_=re.compile(r'root', re.I)):
                text = elem.get_text(strip=True)
                root_match = re.search(r'([ا-ي]{2,4})', text)
                if root_match:
                    root_found = root_match.group(1)
                    break
        
        # Strategy 3: Look for inline root display patterns
        if not root_found:
            # Search entire page for common patterns
            page_text = soup.get_text()
            # Pattern: "الجذر: كتب" or "جذر الكلمة: كتب"
            pattern = re.search(r'(?:الجذر|جذر)[:\s]+([ا-ي]{2,4})', page_text)
            if pattern:
                root_found = pattern.group(1)
        
        if root_found:
            print(f"[AlMaany] Found root: {word} -> {root_found}")
            return root_found, None
        else:
            return None, "Root not found in page"
    
    except Exception as e:
        return None, f"Error: {str(e)}"


async def test_words():
    """Test extraction with sample words."""
    print("=" * 70)
    print("Testing AlMaany Quran Root Extraction (with Cloudflare bypass)")
    print("=" * 70)
    
    test_words = [
        ("كتاب", "كتب"),
        ("الله", "اله"),
        ("الرحمن", "رحم"),
        ("يؤمنون", "امن"),
    ]
    
    for word, expected in test_words:
        print(f"\n{'='*70}")
        print(f"Word: {word} (expected: {expected})")
        print('='*70)
        
        root, error = fetch_root_from_almaany_sync(word)
        
        if root:
            match = "✓" if root == expected else "~"
            print(f"✓ Root: {root} {match}")
        else:
            print(f"✗ Error: {error}")
        
        # Wait between requests to avoid rate limiting
        time.sleep(3)
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_words())
