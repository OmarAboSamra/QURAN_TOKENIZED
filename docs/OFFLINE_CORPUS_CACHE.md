# Offline Corpus Cache Implementation

## Overview

The offline corpus cache provides instant, offline access to Quranic root words with 100% accuracy. It eliminates the need for network requests during normal operation while maintaining the same quality as the online Quranic Arabic Corpus.

## Architecture

### Components

1. **OfflineCorpusCacheExtractor** (`backend/services/root_extractor_v2.py`)
   - Implements the `RootExtractor` interface
   - Loads pre-built cache from JSON file
   - Provides O(1) lookups by `sura:aya:position`
   - Zero network overhead

2. **Cache Builder** (`scripts/build_corpus_cache.py`)
   - Fetches all roots for 114 suras from corpus.quran.com
   - Respects rate limiting (default: 1s between requests)
   - Stores in JSON format with metadata
   - Supports incremental builds (specify sura range)

3. **RootExtractionService** (enhanced)
   - **Priority 1**: Offline corpus cache (instant, 100% accurate)
   - **Priority 2**: Online corpus (fallback for cache misses)
   - **Priority 3**: Algorithmic extractors (fallback when no location)

### Data Format

**Cache File**: `data/corpus_roots_cache.json`

```json
{
  "metadata": {
    "version": "1.0",
    "source": "corpus.quran.com",
    "total_suras": 114,
    "total_verses": 6236,
    "total_words": 77797,
    "suras_covered": "1-114"
  },
  "roots": {
    "1:1:0": "سمو",
    "1:1:1": "اله",
    "1:1:2": "رحم",
    "1:1:3": "رحم",
    ...
  }
}
```

**Key Format**: `"sura:aya:position"` where position is 0-indexed

## Building the Cache

### Full Cache (All 114 Suras)

```bash
# Build complete cache (~2 hours with rate limiting)
python scripts/build_corpus_cache.py \
    --start-sura 1 \
    --end-sura 114 \
    --rate-limit 1.0 \
    --output data/corpus_roots_cache.json \
    --verify
```

### Partial Cache (Single Sura)

```bash
# Build cache for Sura 1 only (testing)
python scripts/build_corpus_cache.py \
    --start-sura 1 \
    --end-sura 1 \
    --rate-limit 0.5 \
    --output data/corpus_roots_cache_test.json
```

### Incremental Updates

```bash
# Update cache for suras 50-60
python scripts/build_corpus_cache.py \
    --start-sura 50 \
    --end-sura 60 \
    --output data/corpus_roots_cache_partial.json
```

## Usage

### Automatic (via RootExtractionService)

The service automatically uses the offline cache when available:

```python
from backend.services.root_extractor_v2 import RootExtractionService

service = RootExtractionService()

# Automatically uses offline cache if location provided
result = await service.extract_root(
    word="بِسْمِ",
    sura=1,
    aya=1,
    position=0
)

print(result['root'])        # "سمو"
print(result['method'])      # "offline_cache"
print(result['confidence'])  # 1.0
```

### Direct Cache Access

```python
from backend.services.root_extractor_v2 import OfflineCorpusCacheExtractor
from pathlib import Path

cache_path = Path("data/corpus_roots_cache.json")
extractor = OfflineCorpusCacheExtractor(cache_path)

result = await extractor.extract_root(
    word="اللَّهِ",
    sura=1,
    aya=1,
    position=1
)

print(result.root)       # "اله"
print(result.success)    # True
print(result.confidence) # 1.0
```

## Testing

### Unit Tests

```bash
# Test offline cache extractor
python scripts/test_offline_cache.py
```

### Integration Tests

```bash
# Run all project tests (includes cache tests)
pytest tests/ -v
```

## Performance

### Benchmarks

| Method | Lookup Time | Network | Accuracy |
|--------|-------------|---------|----------|
| Offline Cache | ~0.1ms | No | 100% |
| Online Corpus | ~1000ms | Yes | 100% |
| Algorithmic | ~10ms | No | 60-70% |

### Benefits

1. **Speed**: 10,000x faster than online corpus
2. **Reliability**: No network failures or rate limits
3. **Offline**: Works without internet connection
4. **Accuracy**: Same 100% accuracy as online corpus
5. **Scalability**: Constant O(1) lookup regardless of corpus size

## Maintenance

### Updating the Cache

The cache should be rebuilt when:
- Corpus.quran.com updates their morphology data
- New verses are added (unlikely for Quran)
- Cache file is corrupted or lost

### Verification

```bash
# Verify cache integrity
python scripts/build_corpus_cache.py \
    --output data/corpus_roots_cache.json \
    --verify
```

### Backup

```bash
# Backup cache file
cp data/corpus_roots_cache.json data/corpus_roots_cache.backup.json
```

## Fallback Behavior

The system gracefully handles cache unavailability:

1. **Cache file missing**: Falls back to online corpus
2. **Cache entry missing**: Falls back to online corpus
3. **No location provided**: Uses algorithmic extractors
4. **All methods fail**: Returns None

## Future Enhancements

1. **Compressed Cache**: Use msgpack or similar for smaller file size
2. **Database Cache**: Store in SQLite for faster cold start
3. **Incremental Updates**: Merge partial caches automatically
4. **Versioning**: Track cache version against corpus updates
5. **Statistics**: Track cache hit rates and performance metrics

## Troubleshooting

### Cache not loading

```python
# Check cache file exists
from pathlib import Path
cache_path = Path("data/corpus_roots_cache.json")
print(f"Cache exists: {cache_path.exists()}")
print(f"Cache size: {cache_path.stat().st_size / 1024 / 1024:.2f} MB")
```

### Cache miss for valid word

```python
# Verify key format
key = f"{sura}:{aya}:{position}"
print(f"Looking for key: {key}")

# Check if verse is in cache
with open("data/corpus_roots_cache.json") as f:
    cache = json.load(f)
    print(f"Key found: {key in cache['roots']}")
```

### Build fails with rate limit errors

```bash
# Increase rate limit delay
python scripts/build_corpus_cache.py \
    --rate-limit 2.0 \  # 2 seconds between requests
    ...
```

## License

The Quranic Arabic Corpus data is available for research and educational use.
Cache file inherits the same license terms.
