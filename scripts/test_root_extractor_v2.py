"""
Test the new multi-source root extractor with sample words.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import (
    RootExtractionService,
    QuranCorpusExtractor,
    AlKhalilExtractor,
)


async def test_single_word():
    """Test extraction for a single word."""
    print("=" * 60)
    print("Testing Multi-Source Root Extraction")
    print("=" * 60)
    
    # Test word: الكتاب (the book)
    test_word = "الكتاب"
    
    print(f"\nTest word: {test_word}")
    print("-" * 60)
    
    # Initialize service
    cache_path = Path(__file__).parent.parent / "data" / "quran_roots_verified.json"
    service = RootExtractionService(cache_path)
    
    # Extract root
    result = await service.extract_root(test_word)
    
    if result:
        print(f"\n✓ Root extracted successfully!")
        print(f"  Root: {result['root']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Agreement: {result['agreement']}")
        print(f"  Sources:")
        for source, root in result['sources'].items():
            print(f"    - {source}: {root}")
    else:
        print(f"\n✗ Failed to extract root")
    
    # Save cache
    service.save_cache()
    
    # Close extractors
    await service.verifier.close()
    
    print("\n" + "=" * 60)


async def test_multiple_words():
    """Test extraction for multiple words."""
    print("\n" + "=" * 60)
    print("Testing Multiple Words")
    print("=" * 60)
    
    test_words = [
        "بسم",      # bismillah
        "الله",     # Allah
        "الرحمن",   # the Most Merciful
        "الكتاب",   # the book
        "يؤمنون",   # they believe
    ]
    
    cache_path = Path(__file__).parent.parent / "data" / "quran_roots_verified.json"
    service = RootExtractionService(cache_path)
    
    for word in test_words:
        print(f"\n{word}:")
        result = await service.extract_root(word)
        
        if result:
            print(f"  ✓ {result['root']} (confidence: {result['confidence']:.2f}, sources: {len(result['sources'])})")
        else:
            print(f"  ✗ Failed")
    
    # Save cache
    service.save_cache()
    
    # Close extractors
    await service.verifier.close()
    
    print("\n" + "=" * 60)


async def main():
    """Run all tests."""
    await test_single_word()
    # await test_multiple_words()  # Uncomment to test multiple words


if __name__ == "__main__":
    asyncio.run(main())
