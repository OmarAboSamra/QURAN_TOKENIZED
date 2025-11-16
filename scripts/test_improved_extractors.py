"""
Test the improved offline extractors (PyArabic and AlKhalil).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import (
    PyArabicExtractor,
    AlKhalilExtractor,
    RootExtractionService,
)


async def test_extractors():
    """Test each extractor individually."""
    print("=" * 70)
    print("Testing Improved Offline Extractors")
    print("=" * 70)
    
    test_words = [
        ("كتاب", "كتب"),    # book -> k-t-b
        ("المسلمون", "سلم"),  # the Muslims -> s-l-m  
        ("الرحمن", "رحم"),  # the Merciful -> r-h-m
        ("يؤمنون", "امن"),  # they believe -> a-m-n
        ("الكتاب", "كتب"),  # the book -> k-t-b
    ]
    
    extractors = [
        PyArabicExtractor(),
        AlKhalilExtractor(),
    ]
    
    for word, expected_root in test_words:
        print(f"\n{'='*70}")
        print(f"Word: {word} (expected root: {expected_root})")
        print('='*70)
        
        for extractor in extractors:
            result = await extractor.extract_root(word)
            
            status = "✓" if result.success else "✗"
            match = "✓" if result.root == expected_root else "~"
            
            print(f"\n[{extractor.name}]")
            print(f"  Status: {status} {'Success' if result.success else 'Failed'}")
            if result.success:
                print(f"  Root: {result.root}")
                print(f"  Match: {match} ({'EXACT' if result.root == expected_root else f'Expected: {expected_root}'})")
                print(f"  Confidence: {result.confidence:.2f}")
            else:
                print(f"  Error: {result.error}")
    
    print("\n" + "=" * 70)


async def test_multi_source_service():
    """Test the full multi-source verification service."""
    print("\n" + "=" * 70)
    print("Testing Multi-Source Verification Service")
    print("=" * 70)
    
    test_words = ["بسم", "الله", "الرحمن", "الرحيم"]
    
    cache_path = Path(__file__).parent.parent / "data" / "quran_roots_verified.json"
    service = RootExtractionService(cache_path)
    
    print("\nExtracting roots with consensus algorithm...")
    print("-" * 70)
    
    for word in test_words:
        print(f"\n{word}:")
        result = await service.extract_root(word)
        
        if result:
            print(f"  ✓ Root: {result['root']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Agreement: {result['agreement']}")
            print(f"  Sources: {', '.join(result['sources'].keys())}")
        else:
            print(f"  ✗ Failed")
    
    service.save_cache()
    print("\n" + "=" * 70)


async def main():
    """Run all tests."""
    await test_extractors()
    await test_multi_source_service()
    print("\nTest Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
