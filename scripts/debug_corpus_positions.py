#!/usr/bin/env python3
"""
Debug: Check what positions corpus returns
"""
import sys
import asyncio
sys.path.insert(0, 'C:/quran-backend')

from backend.services.root_extractor_v2 import QuranCorpusExtractor

async def main():
    extractor = QuranCorpusExtractor()
    
    # Fetch roots for verse 1:1
    roots = await extractor._fetch_verse_roots(1, 1)
    
    print("Corpus verse 1:1 roots by position:")
    for pos, root in sorted(roots.items()):
        print(f"  pos {pos}: {root}")


asyncio.run(main())
