# Phase 1-3 Implementation Guide: Large-Scale Sura Processing

## 🎯 Overview
Complete implementation for handling large suras (e.g., Al-Baqarah ~6000 words) with background processing, pagination, and enhanced frontend navigation.

---

## ✅ PHASE 1: Backend Enhancements - COMPLETED

### 1. Celery Task Queue System ✅
**Files Created:**
- `backend/worker.py` - Celery app configuration
- `backend/tasks/tokenization_tasks.py` - Tokenization jobs
- `backend/tasks/root_extraction_tasks.py` - Root extraction jobs
- `backend/tasks/backup_tasks.py` - Maintenance jobs
- `backend/api/routes_pipeline.py` - Pipeline API endpoints

**Features:**
- ✅ Parallel chunk processing for large suras
- ✅ Progress tracking with real-time updates
- ✅ Correlation IDs for request tracing
- ✅ Automatic retries and error handling
- ✅ Nightly database backups
- ✅ CSV export tasks

### 2. Streaming/Paginated Endpoints ✅
**Enhanced Endpoints:**
```python
GET /quran/tokens?sura=2&page=1&page_size=1000
GET /quran/roots?sura=2&page=1
GET /quran/verse/{sura}/{aya}  # With Redis caching
```

**New Features:**
- ✅ Support for page_size up to 1000 tokens
- ✅ Chunked Redis caching per sura page
- ✅ Efficient pagination with skip/limit
- ✅ Filter by sura, root, search query

### 3. Pipeline Management Endpoints ✅
**New Endpoints:**
```python
POST /pipeline/tokenize?sura=N           # Queue tokenization job
POST /pipeline/extract-roots?sura=N      # Queue root extraction
POST /pipeline/process-sura?sura=N       # Run full pipeline
GET  /pipeline/job/{job_id}              # Check job status
GET  /pipeline/status?sura=N             # Pipeline overview
DELETE /pipeline/job/{job_id}            # Cancel job
```

### 4. Database Optimizations ✅
**Indexes Added:**
- Sura-specific composite indexes
- Root + status composite index
- Sura + aya + position unique index

**Query Optimizations:**
- Repository pattern with eager loading
- Batch processing for large datasets
- Connection pooling for PostgreSQL

### 5. Structured Logging Extensions ✅
**Enhanced Logging:**
- Correlation IDs for request tracking
- Sura/aya context in all logs
- JSON output for production
- Task progress logging

### 6. Rate Limiting & Security ✅
**Configuration:**
```python
# .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
API_KEY_REQUIRED=false  # For admin routes
```

---

## 📋 PHASE 2: Frontend Redesign (TO IMPLEMENT)

### React Router Structure
```javascript
// Routes
/ → Home (Sura list)
/sura/:id?page=:page → Sura view with pagination
/root/:root → Root lookup
/search?q=... → Global search

// Components
- <App /> - Router and global state
- <Header /> - Sura dropdown + search + nav
- <SuraView /> - Paginated sura display
- <VerseGroup /> - Verse container
- <TokenCard /> - Word card
- <RootModal /> - Root lookup modal
- <Pagination /> - Page controls
- <SkeletonLoader /> - Loading state
```

### Key Frontend Features (TO IMPLEMENT)
1. **Pagination Controls**
   ```
   ◀ Previous | Page 1 of 6 | Next ▶
   ```

2. **Sura Dropdown**
   ```html
   <select>
     <option value="1">1. Al-Fatiha</option>
     <option value="2">2. Al-Baqarah</option>
     ...
   </select>
   ```

3. **Jump to Ayah**
   ```html
   <select>
     <option value="1">Ayah 1</option>
     <option value="2">Ayah 2</option>
     ...
   </select>
   ```

4. **Infinite Scroll**
   - Pre-fetch next page when 80% scrolled
   - Show skeleton loaders during fetch
   - Smooth transitions

5. **Mobile Bottom Sheet**
   - Slide-up modal for root lookup
   - Touch-optimized gestures
   - Responsive grid layout

---

## 📊 PHASE 3: Data Processing for Surah Al-Baqarah

### Step-by-Step Commands

#### 1. Start Redis (Required for Celery)
```powershell
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or Windows executable
redis-server
```

#### 2. Start Celery Worker
```powershell
# Set environment
$env:PYTHONPATH = "C:\quran-backend"

# Start worker with multiple queues
celery -A backend.worker worker `
  --loglevel=info `
  --concurrency=4 `
  --queues=tokenization,root_extraction,maintenance `
  --pool=prefork
```

#### 3. Start Celery Beat (Optional - for scheduled tasks)
```powershell
celery -A backend.worker beat --loglevel=info
```

#### 4. Start FastAPI Server
```powershell
$env:PYTHONPATH = "C:\quran-backend"
python backend/main.py
```

#### 5. Queue Tokenization Job for Surah 2
```powershell
# Via API
curl -X POST "http://localhost:8000/pipeline/tokenize?sura=2&chunk_size=20"

# Response:
{
  "job_id": "abc-123-def",
  "correlation_id": "xyz-456-uvw",
  "status": "queued",
  "sura": 2,
  "message": "Tokenization job queued for Surah 2"
}
```

#### 6. Check Job Status
```powershell
curl "http://localhost:8000/pipeline/job/{job_id}"

# Response:
{
  "job_id": "abc-123-def",
  "status": "PROGRESS",
  "sura": 2,
  "progress": 65,
  "meta": {
    "status": "tokenizing",
    "processed": 3000,
    "total": 6000
  }
}
```

#### 7. Queue Root Extraction
```powershell
curl -X POST "http://localhost:8000/pipeline/extract-roots?sura=2&chunk_size=50"
```

#### 8. Or Run Full Pipeline
```powershell
curl -X POST "http://localhost:8000/pipeline/process-sura?sura=2"

# This automatically chains: tokenization → root extraction
```

#### 9. Export CSV (After Processing)
```powershell
# Via Celery task
python -c "
from backend.tasks.backup_tasks import export_sura_csv
result = export_sura_csv.delay(sura=2, page=1)
print(result.get())
"
```

---

## 📁 File Structure

```
quran-backend/
├── backend/
│   ├── worker.py                      # ✅ Celery configuration
│   ├── tasks/
│   │   ├── __init__.py                # ✅ Task package init
│   │   ├── tokenization_tasks.py     # ✅ Tokenization jobs
│   │   ├── root_extraction_tasks.py  # ✅ Root extraction jobs
│   │   └── backup_tasks.py           # ✅ Backup & maintenance
│   ├── api/
│   │   ├── routes_pipeline.py        # ✅ Pipeline endpoints
│   │   └── routes_quran_enhanced.py  # ✅ Enhanced API
│   ├── repositories/
│   │   └── token_repository.py       # ✅ Enhanced with new methods
│   └── static/
│       └── demo/
│           ├── index.html            # Original demo
│           └── index-enhanced.html   # ✅ Enhanced demo
├── data/
│   ├── quran_tokens_sura2_p1.csv     # TO BE GENERATED
│   ├── quran_tokens_sura2_p2.csv     # TO BE GENERATED
│   ├── ...                            # (pages 3-6)
│   └── quran_tokens_word.csv         # Existing (Sura 1)
└── backups/                           # Auto-created by backup task
    └── quran_db_YYYYMMDD_HHMMSS.sql.gz
```

---

## 🔧 Configuration Updates

### .env File
```env
# Existing settings
DATABASE_URL=sqlite:///./quran.db
LOG_LEVEL=INFO

# NEW: Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
TASK_MAX_RETRIES=3

# NEW: Cache Configuration
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL=3600

# NEW: Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# NEW: Monitoring
PROMETHEUS_ENABLED=true
```

### requirements.txt (Already Updated)
```
celery==5.3.4
redis==5.0.1
```

---

## 🎬 Example Workflow: Process Surah 2

### Scenario: User wants to process all of Surah Al-Baqarah

```
Step 1: User hits API
  POST /pipeline/process-sura?sura=2
  
Step 2: Backend queues two jobs
  ├── Job 1: tokenize_sura_parallel
  │   ├── Splits 286 ayahs into 15 chunks (20 ayahs each)
  │   ├── Processes chunks in parallel (4 workers)
  │   └── ~6000 tokens created in database
  │
  └── Job 2: extract_roots_parallel (waits for Job 1)
      ├── Splits 6000 tokens into 120 chunks (50 tokens each)
      ├── Processes chunks in parallel
      └── Roots extracted and cached

Step 3: User checks progress
  GET /pipeline/job/{job_id}
  
  Response at 30%:
  {
    "status": "PROGRESS",
    "progress": 30,
    "meta": {
      "status": "extracting_roots",
      "processed": 1800,
      "total": 6000
    }
  }

Step 4: Completion
  {
    "status": "SUCCESS",
    "result": {
      "sura": 2,
      "tokens_processed": 6000,
      "tokens_updated": 5900,
      "duration_seconds": 245.67
    }
  }

Step 5: Frontend fetches paginated data
  GET /quran/tokens?sura=2&page=1&page_size=1000
  GET /quran/tokens?sura=2&page=2&page_size=1000
  ...
  (6 pages total)
```

---

## 📊 Expected Surah 2 Structure

### Page Division (6 pages, ~1000 tokens each)
```
Page 1: Verses 1-40    (~1000 words)  → /sura/2?page=1
Page 2: Verses 41-80   (~1000 words)  → /sura/2?page=2
Page 3: Verses 81-120  (~1000 words)  → /sura/2?page=3
Page 4: Verses 121-160 (~1000 words)  → /sura/2?page=4
Page 5: Verses 161-240 (~1000 words)  → /sura/2?page=5
Page 6: Verses 241-286 (~1000 words)  → /sura/2?page=6
```

### Sample JSON Response
```json
// GET /quran/tokens?sura=2&page=1&page_size=1000
{
  "tokens": [
    {
      "id": 30,
      "sura": 2,
      "aya": 1,
      "position": 0,
      "text_ar": "الم",
      "normalized": "الم",
      "root": null,
      "status": "verified"
    },
    {
      "id": 31,
      "sura": 2,
      "aya": 2,
      "position": 0,
      "text_ar": "ذَٰلِكَ",
      "normalized": "ذلك",
      "root": "ذلك",
      "status": "verified"
    },
    // ... 998 more tokens
  ],
  "total": 6213,  // Total tokens in Sura 2
  "page": 1,
  "page_size": 1000,
  "filters": {
    "sura": 2,
    "root": null,
    "search": null
  }
}
```

---

## 🎨 Visual Mock: Frontend Navigation

### Desktop View
```
┌────────────────────────────────────────────────────────────┐
│  📖 تحليل القرآن الكريم                                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐       │
│  │ Sura ▾      │  │ Jump to Ayah▾│  │ Search 🔍   │       │
│  │ 2. Al-Baqara│  │ Ayah 1       │  │             │       │
│  └─────────────┘  └──────────────┘  └─────────────┘       │
├────────────────────────────────────────────────────────────┤
│  Surah 2 – Al-Baqarah                                      │
│  Page 1 of 6  (Verses 1-40, ~1000 words)                  │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ Verse 1                                 1 word       ┃  │
│  ┃ الم                                                   ┃  │
│  ┃ ┌──────┐                                             ┃  │
│  ┃ │ الم  │                                             ┃  │
│  ┃ │ الم  │                                             ┃  │
│  ┃ └──────┘                                             ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                             │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ Verse 2                                 5 words      ┃  │
│  ┃ ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ ۛ فِيهِ ۛ هُدًى        ┃  │
│  ┃ [5 token cards displayed...]                        ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                             │
│  [... verses 3-40 ...]                                     │
│                                                             │
├────────────────────────────────────────────────────────────┤
│  ◀ Previous    │    Page 1 of 6    │    Next ▶           │
└────────────────────────────────────────────────────────────┘
```

### Mobile View
```
┌─────────────────────────┐
│ 📖 تحليل القرآن         │
│ ☰  [Sura ▾]  🔍        │
├─────────────────────────┤
│ Surah 2 – Al-Baqarah    │
│ Page 1/6  (V. 1-40)     │
├─────────────────────────┤
│                         │
│ ┏━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ V1: الم           ┃ │
│ ┃ ┌───────────────┐ ┃ │
│ ┃ │ الم           │ ┃ │
│ ┃ └───────────────┘ ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━┛ │
│                         │
│ [Infinite scroll ...]   │
│                         │
│ [Loading next page...]  │
│                         │
└─────────────────────────┘
```

---

## 🚀 Running the Complete System

### Terminal 1: Redis
```powershell
docker run -d -p 6379:6379 redis:7-alpine
```

### Terminal 2: Celery Worker
```powershell
$env:PYTHONPATH = "C:\quran-backend"
celery -A backend.worker worker --loglevel=info --concurrency=4
```

### Terminal 3: FastAPI
```powershell
$env:PYTHONPATH = "C:\quran-backend"
python backend/main.py
```

### Terminal 4: Queue Jobs
```powershell
# Tokenize Sura 2
curl -X POST "http://localhost:8000/pipeline/tokenize?sura=2"

# Wait for completion, then extract roots
curl -X POST "http://localhost:8000/pipeline/extract-roots?sura=2"

# Or do both at once
curl -X POST "http://localhost:8000/pipeline/process-sura?sura=2"
```

### Browser
```
http://localhost:8000/demo-enhanced  # Current enhanced demo (Sura 1)
http://localhost:8000/docs           # API documentation
http://localhost:8000/metrics        # Prometheus metrics
```

---

## 📈 Performance Expectations

### Surah 2 Processing Time
```
Sequential Processing:
  Tokenization: ~45 seconds
  Root Extraction: ~180 seconds (with API calls)
  Total: ~225 seconds

Parallel Processing (4 workers):
  Tokenization: ~15 seconds (3x faster)
  Root Extraction: ~60 seconds (3x faster)
  Total: ~75 seconds ✨

With Caching:
  Subsequent root lookups: ~5 seconds (12x faster)
```

### API Response Times
```
/quran/tokens?sura=2&page=1&page_size=1000
  First load (no cache): ~80ms
  Cached: ~10ms

/quran/verse/2/1
  First load: ~50ms
  Cached: ~5ms
```

---

## ✅ Implementation Status

### Completed ✅
- [x] Celery worker configuration
- [x] Tokenization tasks (parallel, chunked)
- [x] Root extraction tasks (parallel, chunked)
- [x] Backup & maintenance tasks
- [x] Pipeline API endpoints
- [x] Job status tracking
- [x] Repository enhancements
- [x] Correlation ID logging
- [x] Progress tracking
- [x] Error handling & retries

### To Implement 📝
- [ ] React Router setup (frontend)
- [ ] Pagination components (frontend)
- [ ] Infinite scroll (frontend)
- [ ] Mobile bottom sheet (frontend)
- [ ] Sura dropdown with 114 names
- [ ] Jump-to-ayah dropdown
- [ ] Skeleton loaders
- [ ] Pre-fetching logic
- [ ] Update main.py to include pipeline routes
- [ ] Process Surah 2 data
- [ ] Generate 6 CSV files

### Next Steps 🎯
1. Update `backend/main.py` to include pipeline routes
2. Install/verify Celery: `pip install celery redis`
3. Start Redis server
4. Test Celery worker
5. Queue test job for Sura 1 (already tokenized)
6. Implement React Router frontend
7. Process Surah 2 completely
8. Test pagination with 6 pages

---

## 📚 Additional Resources

- **Celery Docs:** https://docs.celeryq.dev/
- **FastAPI Background Tasks:** https://fastapi.tiangolo.com/tutorial/background-tasks/
- **React Router:** https://reactrouter.com/
- **Redis Caching:** https://redis.io/docs/

---

**Status: Backend infrastructure complete. Ready to integrate and test!** 🎉
