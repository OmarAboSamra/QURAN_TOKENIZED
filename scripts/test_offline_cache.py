"""
Test the offline corpus cache extractor.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import (
    OfflineCorpusCacheExtractor,
    RootExtractionService
)


async def test_offline_cache_extractor():
    """Test the offline corpus cache extractor directly."""
    print("=" * 80)
    print("Testing OfflineCorpusCacheExtractor")
    print("=" * 80)
    
    cache_path = Path("data/corpus_roots_cache_test.json")
    
    if not cache_path.exists():
        print(f"Cache file not found: {cache_path}")
        print("Run: python scripts/build_corpus_cache.py --start-sura 1 --end-sura 1")
        return
    
    extractor = OfflineCorpusCacheExtractor(cache_path)
    
    # Test cases from Sura 1
    test_cases = [
        # (word, sura, aya, position, expected_root)
        ("بِسْمِ", 1, 1, 0, "سمو"),
        ("اللَّهِ", 1, 1, 1, "اله"),
        ("الرَّحْمَٰنِ", 1, 1, 2, "رحم"),
        ("الرَّحِيمِ", 1, 1, 3, "رحم"),
        ("الْحَمْدُ", 1, 2, 0, "حمد"),
        ("لِلَّهِ", 1, 2, 1, "اله"),
        ("مَالِكِ", 1, 4, 0, "ملك"),
        ("يَوْمِ", 1, 4, 1, "يوم"),
        ("الدِّينِ", 1, 4, 2, "دين"),
    ]
    
    print(f"\nRunning {len(test_cases)} test cases...\n")
    
    passed = 0
    failed = 0
    
    for word, sura, aya, pos, expected in test_cases:
        result = await extractor.extract_root(word, sura, aya, pos)
        
        if result.success and result.root == expected:
            print(f"✓ {sura}:{aya}:{pos} {word:20s} -> {result.root:8s} (expected: {expected})")
            passed += 1
        else:
            print(f"✗ {sura}:{aya}:{pos} {word:20s} -> {result.root or 'NONE':8s} (expected: {expected})")
            if result.error:
                print(f"  Error: {result.error}")
            failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 80}")


async def test_root_extraction_service():
    """Test the complete RootExtractionService with offline cache."""
    print("\n" + "=" * 80)
    print("Testing RootExtractionService with Offline Cache")
    print("=" * 80)
    
    cache_path = Path("data/quran_roots_verified.json")
    corpus_cache_path = Path("data/corpus_roots_cache_test.json")
    
    service = RootExtractionService(
        cache_path=cache_path,
        corpus_cache_path=corpus_cache_path
    )
    
    # Test cases
    test_cases = [
        # (word, sura, aya, position, expected_root, expected_method)
        ("بِسْمِ", 1, 1, 0, "سمو", "offline_cache"),
        ("اللَّهِ", 1, 1, 1, "اله", "offline_cache"),
        ("الرَّحْمَٰنِ", 1, 1, 2, "رحم", "offline_cache"),
    ]
    
    print(f"\nRunning {len(test_cases)} test cases...\n")
    
    for word, sura, aya, pos, expected_root, expected_method in test_cases:
        result = await service.extract_root(word, sura, aya, pos)
        
        if result:
            method = result.get('method')
            root = result.get('root')
            confidence = result.get('confidence')
            
            status = "✓" if root == expected_root else "✗"
            method_status = "✓" if method == expected_method else "✗"
            
            print(f"{status} {sura}:{aya}:{pos} {word:20s}")
            print(f"   Root: {root} (expected: {expected_root})")
            print(f"   {method_status} Method: {method} (expected: {expected_method})")
            print(f"   Confidence: {confidence}")
        else:
            print(f"✗ {sura}:{aya}:{pos} {word:20s} -> FAILED")
    
    print(f"\n{'=' * 80}")


async def test_fallback_to_online():
    """Test fallback from offline cache to online corpus for missing entries."""
    print("\n" + "=" * 80)
    print("Testing Fallback to Online Corpus")
    print("=" * 80)
    
    cache_path = Path("data/quran_roots_verified.json")
    corpus_cache_path = Path("data/corpus_roots_cache_test.json")  # Only has Sura 1
    
    service = RootExtractionService(
        cache_path=cache_path,
        corpus_cache_path=corpus_cache_path
    )
    
    # Test with a verse from Sura 2 (not in cache)
    word = "الْكِتَابُ"
    sura, aya, pos = 2, 2, 1
    
    print(f"\nTesting word from Sura 2 (not in offline cache): {word}")
    print(f"Location: {sura}:{aya}:{pos}")
    print("Expected: Should fall back to online corpus\n")
    
    result = await service.extract_root(word, sura, aya, pos)
    
    if result:
        print(f"✓ Root extracted: {result['root']}")
        print(f"  Method: {result['method']}")
        print(f"  Confidence: {result['confidence']}")
        
        if result['method'] == 'online_corpus':
            print("  ✓ Correctly fell back to online corpus!")
        else:
            print(f"  ⚠ Expected online_corpus, got {result['method']}")
    else:
        print("✗ Failed to extract root")


async def main():
    """Run all tests."""
    await test_offline_cache_extractor()
    await test_root_extraction_service()
    await test_fallback_to_online()
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
