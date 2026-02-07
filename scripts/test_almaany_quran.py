"""
AlMaany Quran Root Extractor - Direct Implementation

This extractor uses AlMaany's Quran-specific word search to extract roots.
URL pattern: https://www.almaany.com/quran-b/search?q={word}
"""

import asyncio
import re
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from bs4 import BeautifulSoup


async def fetch_root_from_almaany(word: str) -> tuple[str, str]:
    """
    Fetch root for a word from AlMaany Quran section.
    
    Returns:
        tuple: (root, error) - root if found, else None with error message
    """
    url = "https://www.almaany.com/quran-b/"
    
    # Create client with browser-like headers
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
    ) as client:
        try:
            # First, get the main page to establish session
            print(f"[AlMaany] Getting main page...")
            response = await client.get(url)
            
            if response.status_code == 403:
                return None, "Cloudflare blocking"
            
            response.raise_for_status()
            
            # Wait a bit to avoid rate limiting
            await asyncio.sleep(2)
            
            # Now search for the word
            search_url = f"{url}search"
            params = {"q": word}
            
            print(f"[AlMaany] Searching for: {word}")
            search_response = await client.get(search_url, params=params)
            search_response.raise_for_status()
            
            soup = BeautifulSoup(search_response.text, 'html.parser')
            
            # Look for root in the results
            # AlMaany typically shows root in a specific structure
            # Try multiple strategies
            
            # Strategy 1: Look for "الجذر" (root) label
            for text in soup.find_all(text=re.compile(r'الجذر|جذر')):
                parent = text.find_parent()
                if parent:
                    # Get the next element or sibling
                    root_elem = parent.find_next_sibling() or parent.find_next()
                    if root_elem:
                        root_text = root_elem.get_text(strip=True)
                        # Extract Arabic root
                        root_match = re.search(r'([ا-ي]{2,4})', root_text)
                        if root_match:
                            root = root_match.group(1)
                            print(f"[AlMaany] Found root: {word} -> {root}")
                            return root, None
            
            # Strategy 2: Look in table cells
            for cell in soup.find_all(['td', 'div', 'span'], class_=re.compile(r'root|جذر', re.I)):
                text = cell.get_text(strip=True)
                root_match = re.search(r'([ا-ي]{2,4})', text)
                if root_match:
                    root = root_match.group(1)
                    print(f"[AlMaany] Found root: {word} -> {root}")
                    return root, None
            
            # Strategy 3: Look for patterns in text
            page_text = soup.get_text()
            # Look for "الجذر: XXX" or similar patterns
            pattern_match = re.search(r'(?:الجذر|جذر)[\s:]+([ا-ي]{2,4})', page_text)
            if pattern_match:
                root = pattern_match.group(1)
                print(f"[AlMaany] Found root: {word} -> {root}")
                return root, None
            
            return None, "Root not found in page"
            
        except httpx.HTTPStatusError as e:
            return None, f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
        except Exception as e:
            return None, f"Error: {str(e)}"


async def test_words():
    """Test extraction with sample words."""
    print("=" * 70)
    print("Testing AlMaany Quran Root Extraction")
    print("=" * 70)
    
    test_words = [
        "كتاب",
        "الله",
        "رحمن",
        "مسلم",
    ]
    
    for word in test_words:
        print(f"\n{'='*70}")
        print(f"Word: {word}")
        print('='*70)
        
        root, error = await fetch_root_from_almaany(word)
        
        if root:
            print(f"✓ Root: {root}")
        else:
            print(f"✗ Error: {error}")
        
        # Wait between requests
        await asyncio.sleep(3)
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_words())
