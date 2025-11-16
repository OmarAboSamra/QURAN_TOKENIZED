"""
Quick test of multi-source root extractor without running full pipeline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.services.root_extractor_v2 import AlKhalilExtractor


async def test_algorithmic():
    """Test the algorithmic extractor (doesn't require internet)."""
    print("=" * 60)
    print("Testing AlKhalil Algorithmic Extractor")
    print("=" * 60)
    
    extractor = AlKhalilExtractor()
    
    test_words = [
        ("الكتاب", "كتب"),     # the book -> k-t-b
        ("المسلمون", "سلم"),   # the Muslims -> s-l-m
        ("يؤمنون", "امن"),     # they believe -> a-m-n
        ("الرحمن", "رحم"),     # the Most Merciful -> r-h-m
    ]
    
    print("\nTesting algorithmic root extraction:")
    print("-" * 60)
    
    for word, expected in test_words:
        result = await extractor.extract_root(word)
        
        status = "✓" if result.success else "✗"
        print(f"{status} {word:15} -> {result.root if result.root else 'FAILED':10} (expected: {expected})")
        
        if result.error:
            print(f"  Error: {result.error}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_algorithmic())
