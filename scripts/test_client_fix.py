"""
Test the fixed multi-source extractor to verify client lifecycle fix.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import RootExtractionService


async def test_multiple_words():
    """Test extraction for multiple words to verify client reuse."""
    print("=" * 60)
    print("Testing Client Lifecycle Fix")
    print("=" * 60)
    
    test_words = [
        "بسم",      # bismillah
        "الله",     # Allah
        "الرحمن",   # the Most Merciful
    ]
    
    cache_path = Path(__file__).parent.parent / "data" / "quran_roots_verified.json"
    service = RootExtractionService(cache_path)
    
    print("\nExtracting roots for multiple words...")
    print("-" * 60)
    
    for i, word in enumerate(test_words, 1):
        print(f"\n[{i}/{len(test_words)}] {word}:")
        result = await service.extract_root(word)
        
        if result:
            print(f"  ✓ Root: {result['root']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Sources: {len(result['sources'])}")
            for source, root in result['sources'].items():
                print(f"    - {source}: {root}")
        else:
            print(f"  ✗ Failed to extract root")
    
    # Save cache
    service.save_cache()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_multiple_words())
