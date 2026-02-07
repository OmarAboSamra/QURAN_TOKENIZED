#!/usr/bin/env python3
"""
Test new Corpus extractor integrated into RootExtractionService
"""
import sys
import asyncio
sys.path.insert(0, 'C:/quran-backend')

from backend.services.root_extractor_v2 import RootExtractionService

async def test_corpus_integration():
    print("="*70)
    print("Testing Corpus Extractor Integration")
    print("="*70)
    
    service = RootExtractionService()
    
    # Test tokens from Sura 1:1
    test_cases = [
        ("بسم", 1, 1, 0, "سمو"),   # bis'mi -> smw -> سمو (name)
        ("الله", 1, 1, 1, "اله"),  # l-lahi -> Alh -> اله (Allah)
        ("الرحمن", 1, 1, 2, "رحم"), # l-rahmani -> rHm -> رحم (mercy)
        ("الرحيم", 1, 1, 3, "رحم"), # l-rahimi -> rHm -> رحم (mercy)
    ]
    
    correct = 0
    total = len(test_cases)
    
    for word, sura, aya, pos, expected_root in test_cases:
        result = await service.extract_root(word, sura=sura, aya=aya, position=pos)
        
        if result:
            root = result['root']
            method = result.get('method', 'unknown')
            confidence = result.get('confidence', 0)
            
            match = root == expected_root
            status = '✓' if match else '✗'
            
            print(f"{status} {sura}:{aya}:{pos} {word:10} -> {root:6} (expected: {expected_root}, method: {method}, conf: {confidence:.0%})")
            
            if match:
                correct += 1
        else:
            print(f"✗ {sura}:{aya}:{pos} {word:10} -> FAILED")
    
    print(f"\n{correct}/{total} correct ({100*correct/total:.0%})")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_corpus_integration())
