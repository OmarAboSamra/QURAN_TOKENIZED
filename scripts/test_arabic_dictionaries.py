"""
Test the new Arabic dictionary extractors (AlMaany and Baheth).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import (
    AlMaanyExtractor,
    BahethExtractor,
    AlKhalilExtractor,
)


async def test_extractors():
    """Test each extractor individually."""
    print("=" * 70)
    print("Testing Arabic Dictionary Extractors")
    print("=" * 70)
    
    test_words = [
        ("كتاب", "كتب"),    # book -> k-t-b
        ("مسلم", "سلم"),    # Muslim -> s-l-m  
        ("رحمن", "رحم"),    # merciful -> r-h-m
    ]
    
    extractors = [
        AlMaanyExtractor(),
        BahethExtractor(),
        AlKhalilExtractor(),
    ]
    
    for word, expected_root in test_words:
        print(f"\n{'='*70}")
        print(f"Word: {word} (expected root: {expected_root})")
        print('='*70)
        
        for extractor in extractors:
            result = await extractor.extract_root(word)
            
            status = "✓" if result.success else "✗"
            match = "✓" if result.root == expected_root else "✗"
            
            print(f"\n[{extractor.name}]")
            print(f"  Status: {status} {'Success' if result.success else 'Failed'}")
            if result.success:
                print(f"  Root: {result.root}")
                print(f"  Match: {match} ({'CORRECT' if result.root == expected_root else f'Expected: {expected_root}'})")
                print(f"  Confidence: {result.confidence:.2f}")
            else:
                print(f"  Error: {result.error}")
        
        # Small delay between words
        await asyncio.sleep(1)
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_extractors())
