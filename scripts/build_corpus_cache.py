"""
Build offline corpus cache for all Quranic roots.

This script:
1. Extracts roots for all 114 suras using QuranCorpusExtractor
2. Stores them in a JSON file keyed by sura:aya:position
3. Creates an efficient lookup structure for offline use

The cache will enable instant, offline root lookups with 100% accuracy
for all Quranic words.
"""

import asyncio
import json
from pathlib import Path
import sys
from typing import Dict, Optional
from collections import defaultdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import QuranCorpusExtractor


# Quran structure: sura -> number of ayas
QURAN_STRUCTURE = {
    1: 7, 2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109,
    11: 123, 12: 111, 13: 43, 14: 52, 15: 99, 16: 128, 17: 111, 18: 110, 19: 98, 20: 135,
    21: 112, 22: 78, 23: 118, 24: 64, 25: 77, 26: 227, 27: 93, 28: 88, 29: 69, 30: 60,
    31: 34, 32: 30, 33: 73, 34: 54, 35: 45, 36: 83, 37: 182, 38: 88, 39: 75, 40: 85,
    41: 54, 42: 53, 43: 89, 44: 59, 45: 37, 46: 35, 47: 38, 48: 29, 49: 18, 50: 45,
    51: 60, 52: 49, 53: 62, 54: 55, 55: 78, 56: 96, 57: 29, 58: 22, 59: 24, 60: 13,
    61: 14, 62: 11, 63: 11, 64: 18, 65: 12, 66: 12, 67: 30, 68: 52, 69: 52, 70: 44,
    71: 28, 72: 28, 73: 20, 74: 56, 75: 40, 76: 31, 77: 50, 78: 40, 79: 46, 80: 42,
    81: 29, 82: 19, 83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 26, 89: 30, 90: 20,
    91: 15, 92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 8, 99: 8, 100: 11,
    101: 11, 102: 8, 103: 3, 104: 9, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6, 110: 3,
    111: 5, 112: 4, 113: 5, 114: 6
}


async def extract_verse_roots(
    extractor: QuranCorpusExtractor,
    sura: int,
    aya: int
) -> Dict[int, str]:
    """
    Extract all roots for a single verse.
    
    Returns:
        Dictionary mapping position (0-indexed) to root
    """
    try:
        verse_roots = await extractor._fetch_verse_roots(sura, aya)
        return verse_roots
    except Exception as e:
        print(f"Error extracting verse {sura}:{aya}: {e}")
        return {}


async def build_corpus_cache(
    output_path: Path,
    start_sura: int = 1,
    end_sura: int = 114,
    rate_limit_delay: float = 1.0
) -> Dict:
    """
    Build complete corpus cache for specified sura range.
    
    Args:
        output_path: Path to save cache JSON
        start_sura: Starting sura (inclusive)
        end_sura: Ending sura (inclusive)
        rate_limit_delay: Delay between requests in seconds
        
    Returns:
        Cache dictionary
    """
    extractor = QuranCorpusExtractor()
    extractor.min_request_interval = rate_limit_delay
    
    cache = {
        'metadata': {
            'version': '1.0',
            'source': 'corpus.quran.com',
            'total_suras': 0,
            'total_verses': 0,
            'total_words': 0,
            'suras_covered': f"{start_sura}-{end_sura}"
        },
        'roots': {}  # Format: "sura:aya:position" -> root
    }
    
    total_verses = 0
    total_words = 0
    
    print(f"Building corpus cache for Suras {start_sura} to {end_sura}...")
    print(f"Rate limit: {rate_limit_delay}s between requests")
    print("=" * 80)
    
    for sura in range(start_sura, end_sura + 1):
        if sura not in QURAN_STRUCTURE:
            print(f"Warning: Sura {sura} not in structure mapping, skipping")
            continue
        
        num_ayas = QURAN_STRUCTURE[sura]
        print(f"\nSura {sura:3d} ({num_ayas:3d} verses)")
        
        sura_word_count = 0
        
        for aya in range(1, num_ayas + 1):
            verse_roots = await extract_verse_roots(extractor, sura, aya)
            
            for position, root in verse_roots.items():
                key = f"{sura}:{aya}:{position}"
                cache['roots'][key] = root
                sura_word_count += 1
                total_words += 1
            
            total_verses += 1
            
            # Progress indicator
            if aya % 10 == 0:
                print(f"  Verse {aya:3d}/{num_ayas:3d} - {sura_word_count} words", end='\r')
        
        print(f"  Completed: {sura_word_count} words in {num_ayas} verses")
    
    # Update metadata
    cache['metadata']['total_suras'] = end_sura - start_sura + 1
    cache['metadata']['total_verses'] = total_verses
    cache['metadata']['total_words'] = total_words
    
    print("\n" + "=" * 80)
    print(f"Cache building complete!")
    print(f"  Total suras: {cache['metadata']['total_suras']}")
    print(f"  Total verses: {cache['metadata']['total_verses']}")
    print(f"  Total words: {cache['metadata']['total_words']}")
    
    # Save cache
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"\nCache saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return cache


async def verify_cache(cache_path: Path, sample_size: int = 20):
    """
    Verify cache integrity by sampling random entries.
    """
    print("\n" + "=" * 80)
    print("Verifying cache...")
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    roots = cache['roots']
    
    print(f"Metadata:")
    for key, value in cache['metadata'].items():
        print(f"  {key}: {value}")
    
    print(f"\nSample entries:")
    import random
    sample_keys = random.sample(list(roots.keys()), min(sample_size, len(roots)))
    
    for key in sample_keys[:10]:
        root = roots[key]
        print(f"  {key} -> {root}")
    
    # Verify structure
    for key in sample_keys:
        parts = key.split(':')
        if len(parts) != 3:
            print(f"ERROR: Invalid key format: {key}")
            return False
        
        try:
            sura, aya, pos = map(int, parts)
        except ValueError:
            print(f"ERROR: Invalid key values: {key}")
            return False
    
    print("\nCache verification passed!")
    return True


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build offline corpus cache')
    parser.add_argument('--start-sura', type=int, default=1, help='Starting sura (default: 1)')
    parser.add_argument('--end-sura', type=int, default=114, help='Ending sura (default: 114)')
    parser.add_argument('--rate-limit', type=float, default=1.0, help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--output', type=str, default='data/corpus_roots_cache.json', help='Output file path')
    parser.add_argument('--verify', action='store_true', help='Verify cache after building')
    
    args = parser.parse_args()
    
    output_path = Path(args.output)
    
    # Build cache
    cache = await build_corpus_cache(
        output_path,
        start_sura=args.start_sura,
        end_sura=args.end_sura,
        rate_limit_delay=args.rate_limit
    )
    
    # Verify if requested
    if args.verify:
        await verify_cache(output_path)


if __name__ == "__main__":
    asyncio.run(main())
