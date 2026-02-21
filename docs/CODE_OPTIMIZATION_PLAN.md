# Code Optimization Plan

> **Purpose**: Concrete code-level improvements to make the existing codebase
> more correct, performant, and maintainable. Each item is self-contained
> and can be implemented independently.
> Ordered by priority (bugs/broken code first, then performance, then style).

> **Status**: ALL 14 ITEMS IMPLEMENTED — see commit history for details.

---

## C1 · Wire `configure_logging()` in App Startup (BUG) ✅ DONE

**File**: `backend/main.py` → lifespan function

**Problem**: `backend/logging_config.py` defines `configure_logging()` which sets up structlog processors, but it is never called. All `get_logger()` calls use an unconfigured structlog, producing plain unstructured output.

**Fix**:
```python
# In lifespan(), before "Initializing database..."
from backend.logging_config import configure_logging
configure_logging()
```

---

## C2 · Wire Prometheus Instrumentator (BUG) ✅ DONE

**File**: `backend/metrics.py` + `backend/main.py`

**Problem**: `get_instrumentator()` creates an Instrumentator but it is never attached to the FastAPI app. Additionally, the `.add()` calls use an incorrect API (`Instrumentator.metrics.default()` does not exist).

**Fix**:
```python
# In main.py after app creation:
if settings.prometheus_enabled:
    from backend.metrics import get_instrumentator
    instrumentator = get_instrumentator()
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics")
```
Also fix `get_instrumentator()` to use the correct prometheus-fastapi-instrumentator API.

---

## C3 · Use `settings.cors_origins_list` Instead of `["*"]` (BUG) ✅ DONE

**File**: `backend/main.py` line with `allow_origins=["*"]`

**Problem**: `config.py` defines `cors_origins_list` property parsing `api_cors_origins`, but `main.py` hardcodes `allow_origins=["*"]`, making the config setting dead code.

**Fix**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    ...
)
```

---

## C4 · Split `root_extractor_v2.py` Into Separate Modules (REFACTOR) ✅ DONE

**File**: `backend/services/root_extractor_v2.py` (1204 lines)

**Problem**: One file contains 6 extractor classes, a verifier, and a service — making it hard to navigate, test, or modify a single extractor.

**Fix**:
```
backend/services/extractors/
    __init__.py
    base.py              → RootExtractor ABC + RootExtractionResult
    quran_corpus.py      → QuranCorpusExtractor (line 100-262)
    offline_cache.py     → OfflineCorpusCacheExtractor (line 263-363)
    almaany.py           → AlMaanyExtractor (line 364-473)
    baheth.py            → BahethExtractor (line 474-580)
    pyarabic_ext.py      → PyArabicExtractor (line 581-723)
    alkhalil.py          → AlKhalilExtractor (line 724-860)
backend/services/
    multi_source_verifier.py  → MultiSourceVerifier (line 861-1071)
    root_extraction_service.py → RootExtractionService (line 1072-1204)
```

---

## C5 · Add Proper Error Handling in Route Handlers (IMPROVEMENT) ✅ DONE

**File**: `backend/api/routes_quran_enhanced.py`

**Problem**: Most endpoints catch no exceptions from the database layer. If the DB is down or a query fails, the user gets a raw 500 with a stack trace.

**Fix**:
```python
from sqlalchemy.exc import SQLAlchemyError

@router.get("/tokens")
async def get_tokens(...):
    try:
        tokens = await token_repo.aget_filtered(...)
        ...
    except SQLAlchemyError as e:
        logger.error("db_error", error=str(e))
        raise HTTPException(status_code=503, detail="Database unavailable")
```

---

## C6 · Replace `time.time()` with `time.perf_counter()` (IMPROVEMENT) ✅ DONE

**File**: `backend/api/routes_quran_enhanced.py` (6 occurrences)

**Problem**: `time.time()` is wall-clock time affected by system clock adjustments. `time.perf_counter()` is monotonic and more accurate for measuring request duration.

**Fix**: Global find-replace `time.time()` → `time.perf_counter()` in route files.

---

## C7 · Avoid Duplicate Imports in `get_stats` Endpoint (CLEANUP) ✅ DONE

**File**: `backend/api/routes_quran_enhanced.py`, `get_stats()` function

**Problem**: `func`, `select`, and `Token` are imported at the top of the file but also re-imported inside the `get_stats` function body.

**Fix**: Remove the local imports:
```python
async def get_stats(...):
    # Remove these lines:
    # from sqlalchemy import func, select
    # from backend.models import Token
```

---

## C8 · Add `__repr__` to Verse Model (CLEANUP) ✅ DONE (already adequate)

**File**: `backend/models/verse_model.py`

**Problem**: Root and Token have informative `__repr__` but Verse's is minimal.

**Fix**: Already has a basic `__repr__`. This is low priority.

---

## C9 · Add Type Hints to `root_extractor_v2.py` Functions (IMPROVEMENT) ✅ DONE

**File**: `backend/services/root_extractor_v2.py`

**Problem**: Several internal methods lack return type hints, making IDE navigation harder.

**Fix**: Audit all methods in the 6 extractor classes and add `-> Optional[str]`, `-> RootExtractionResult`, etc.

---

## C10 · Use `selectinload` for Verse → Token Queries (PERFORMANCE) ✅ DONE (implemented in D1)

**File**: `backend/repositories/token_repository.py`

**Problem**: `aget_verse_tokens` runs a separate query. If a Token→Verse relationship existed (see Design D1), a single query with `selectinload` would fetch verse + tokens in one round-trip.

**Fix**: Implement after D1 (ORM relationships) from the Design Review Plan.

---

## C11 · Cache `get_stats()` Response (PERFORMANCE) ✅ DONE

**File**: `backend/api/routes_quran_enhanced.py`

**Problem**: The stats endpoint runs 3 aggregate queries (`COUNT`, `COUNT DISTINCT`) on every call. These are expensive and rarely change.

**Fix**:
```python
cached_stats = await cache.get_json("stats:global")
if cached_stats:
    return StatsResponse(**cached_stats)
# ... compute stats ...
await cache.set_json("stats:global", response_data, ttl=300)  # 5 min
```

---

## C12 · Add Input Validation for Arabic Text (IMPROVEMENT) ✅ DONE

**File**: `backend/api/routes_quran_enhanced.py`, search endpoint

**Problem**: No validation that the search query `q` actually contains Arabic characters. Non-Arabic queries silently return empty results.

**Fix**: Add a Pydantic validator or a pre-check:
```python
import re
if not re.search(r'[\u0600-\u06FF]', q):
    raise HTTPException(400, "Search query must contain Arabic text")
```

---

## C13 · Remove Unused `arabic_reshaper` Import (CLEANUP) ✅ DONE

**File**: `backend/services/tokenizer_service.py`

**Problem**: `import arabic_reshaper` is at the top but never used anywhere in the file.

**Fix**: Remove the import line.

---

## C14 · Add Pagination Metadata to All List Responses (IMPROVEMENT) ✅ DONE

**File**: `backend/api/schemas.py`

**Problem**: `TokenListResponse` has `total`, `page`, `page_size` but no `total_pages` computed field, making it harder for frontends to build pagination controls.

**Fix**:
```python
class TokenListResponse(BaseModel):
    ...
    @computed_field
    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0
```

---

## Summary Priority Matrix

| ID  | Type        | Effort | Impact |
|-----|-------------|--------|--------|
| C1  | BUG         | Low    | High   |
| C2  | BUG         | Low    | Medium |
| C3  | BUG         | Low    | Medium |
| C4  | REFACTOR    | Medium | High   |
| C5  | IMPROVEMENT | Low    | High   |
| C6  | IMPROVEMENT | Low    | Low    |
| C7  | CLEANUP     | Low    | Low    |
| C8  | CLEANUP     | Low    | Low    |
| C9  | IMPROVEMENT | Medium | Medium |
| C10 | PERFORMANCE | Medium | High   |
| C11 | PERFORMANCE | Low    | Medium |
| C12 | IMPROVEMENT | Low    | Medium |
| C13 | CLEANUP     | Low    | Low    |
| C14 | IMPROVEMENT | Low    | Medium |

Recommended execution order: **C1 → C2 → C3 → C13 → C7 → C5 → C6 → C12 → C11 → C14 → C4 → C9 → C10**
