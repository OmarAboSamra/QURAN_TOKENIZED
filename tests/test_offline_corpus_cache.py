"""
Comprehensive tests for offline corpus cache extractor.
"""

import pytest
import asyncio
import json
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.root_extractor_v2 import (
    OfflineCorpusCacheExtractor,
    RootExtractionService,
    MultiSourceVerifier,
    PyArabicExtractor,
    RootExtractionResult
)


@pytest.fixture
def test_cache_path():
    """Fixture providing path to test cache."""
    return Path("data/corpus_roots_cache_test.json")


@pytest.fixture
def offline_extractor(test_cache_path):
    """Fixture providing offline cache extractor."""
    return OfflineCorpusCacheExtractor(test_cache_path)


@pytest.mark.asyncio
async def test_offline_extractor_loads_cache(test_cache_path):
    """Test that offline extractor loads cache successfully."""
    extractor = OfflineCorpusCacheExtractor(test_cache_path)
    
    assert len(extractor.cache) > 0
    assert extractor.metadata.get('total_words', 0) > 0
    assert extractor.metadata.get('source') == 'corpus.quran.com'


@pytest.mark.asyncio
async def test_offline_extractor_valid_lookup(offline_extractor):
    """Test offline extractor with valid lookup."""
    # Test known entry from Sura 1
    result = await offline_extractor.extract_root(
        word="بِسْمِ",
        sura=1,
        aya=1,
        position=0
    )
    
    assert result.success
    assert result.root == "سمو"
    assert result.confidence == 1.0
    assert result.source == "offline_corpus_cache"
    assert result.error is None


@pytest.mark.asyncio
async def test_offline_extractor_multiple_words(offline_extractor):
    """Test offline extractor with multiple words from same verse."""
    words = [
        ("بِسْمِ", 1, 1, 0, "سمو"),
        ("اللَّهِ", 1, 1, 1, "اله"),
        ("الرَّحْمَٰنِ", 1, 1, 2, "رحم"),
        ("الرَّحِيمِ", 1, 1, 3, "رحم"),
    ]
    
    for word, sura, aya, pos, expected_root in words:
        result = await offline_extractor.extract_root(word, sura, aya, pos)
        assert result.success, f"Failed for {word}"
        assert result.root == expected_root, f"Expected {expected_root}, got {result.root}"


@pytest.mark.asyncio
async def test_offline_extractor_missing_location():
    """Test offline extractor with missing location parameters."""
    extractor = OfflineCorpusCacheExtractor(Path("data/corpus_roots_cache_test.json"))
    
    # Missing sura
    result = await extractor.extract_root(word="test", sura=None, aya=1, position=0)
    assert not result.success
    assert "required" in result.error.lower()
    
    # Missing aya
    result = await extractor.extract_root(word="test", sura=1, aya=None, position=0)
    assert not result.success
    assert "required" in result.error.lower()
    
    # Missing position
    result = await extractor.extract_root(word="test", sura=1, aya=1, position=None)
    assert not result.success
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_offline_extractor_invalid_position():
    """Test offline extractor with invalid position."""
    extractor = OfflineCorpusCacheExtractor(Path("data/corpus_roots_cache_test.json"))
    
    # Position that doesn't exist in verse
    result = await extractor.extract_root(
        word="test",
        sura=1,
        aya=1,
        position=999
    )
    
    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_root_service_uses_offline_cache():
    """Test that RootExtractionService prioritizes offline cache."""
    service = RootExtractionService(
        corpus_cache_path=Path("data/corpus_roots_cache_test.json")
    )
    
    result = await service.extract_root(
        word="بِسْمِ",
        sura=1,
        aya=1,
        position=0
    )
    
    assert result is not None
    assert result['root'] == "سمو"
    assert result['method'] == "offline_cache"
    assert result['confidence'] == 1.0


@pytest.mark.asyncio
async def test_multi_source_verifier_trust_weights():
    """Test that MultiSourceVerifier uses trust weights correctly."""
    extractors = [PyArabicExtractor()]
    verifier = MultiSourceVerifier(extractors)
    
    # Check that trust weights are defined
    assert 'offline_corpus_cache' in verifier.SOURCE_WEIGHTS
    assert 'qurancorpus' in verifier.SOURCE_WEIGHTS
    assert 'pyarabic' in verifier.SOURCE_WEIGHTS
    
    # Corpus sources should have highest weight
    assert verifier.SOURCE_WEIGHTS['offline_corpus_cache'] >= 10.0
    assert verifier.SOURCE_WEIGHTS['qurancorpus'] >= 10.0
    
    # Algorithmic sources should have lower weight
    assert verifier.SOURCE_WEIGHTS['pyarabic'] < 10.0


@pytest.mark.asyncio
async def test_cache_handles_missing_file():
    """Test that extractor handles missing cache file gracefully."""
    non_existent_path = Path("data/does_not_exist.json")
    extractor = OfflineCorpusCacheExtractor(non_existent_path)
    
    # Should load with empty cache
    assert len(extractor.cache) == 0
    
    # Lookups should fail gracefully
    result = await extractor.extract_root(
        word="test",
        sura=1,
        aya=1,
        position=0
    )
    
    assert not result.success


@pytest.mark.asyncio
async def test_offline_cache_all_sura1_verses():
    """Test offline cache for all verses in Sura 1."""
    extractor = OfflineCorpusCacheExtractor(Path("data/corpus_roots_cache_test.json"))
    
    # Sura 1 has 7 verses
    total_words = 0
    
    for aya in range(1, 8):
        # Try positions 0-10 (max words in any verse of Sura 1)
        for pos in range(10):
            result = await extractor.extract_root(
                word=f"test_{aya}_{pos}",
                sura=1,
                aya=aya,
                position=pos
            )
            
            if result.success:
                total_words += 1
                assert result.root is not None
                assert result.confidence == 1.0
    
    # Sura 1 should have ~23 words
    assert total_words >= 20
    assert total_words <= 30


@pytest.mark.asyncio
async def test_service_fallback_to_online():
    """Test service falls back to online corpus when cache misses."""
    # Use test cache that only has Sura 1
    service = RootExtractionService(
        corpus_cache_path=Path("data/corpus_roots_cache_test.json")
    )
    
    # Try word from Sura 2 (not in test cache)
    result = await service.extract_root(
        word="الْكِتَابُ",
        sura=2,
        aya=2,
        position=1
    )
    
    # Should succeed via online fallback or algorithmic
    assert result is not None
    assert result['root'] is not None
    assert result['method'] in ['online_corpus', 'algorithmic']


def test_cache_format():
    """Test that cache file has correct format."""
    cache_path = Path("data/corpus_roots_cache_test.json")
    
    if not cache_path.exists():
        pytest.skip("Test cache not available")
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check top-level structure
    assert 'metadata' in data
    assert 'roots' in data
    
    # Check metadata fields
    metadata = data['metadata']
    assert 'version' in metadata
    assert 'source' in metadata
    assert 'total_words' in metadata
    
    # Check roots format
    roots = data['roots']
    assert isinstance(roots, dict)
    
    # Check key format: "sura:aya:position"
    for key, root in roots.items():
        parts = key.split(':')
        assert len(parts) == 3
        
        sura, aya, pos = parts
        assert sura.isdigit()
        assert aya.isdigit()
        assert pos.isdigit()
        
        # Root should be Arabic text
        assert isinstance(root, str)
        assert len(root) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
