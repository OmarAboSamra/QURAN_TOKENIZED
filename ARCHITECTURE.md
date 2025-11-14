# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │   cURL/HTTP  │  │  Frontend    │          │
│  │   /docs      │  │   Client     │  │   App        │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            │ HTTP/REST
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  main.py - FastAPI Application                             │ │
│  │    • CORS Middleware                                        │ │
│  │    • Request/Response handling                              │ │
│  │    • OpenAPI documentation                                  │ │
│  └────────────┬────────────────────────┬──────────────────────┘ │
│               │                        │                         │
│  ┌────────────▼──────────┐  ┌─────────▼──────────────┐         │
│  │  routes_meta.py       │  │  routes_quran.py       │         │
│  │  • /meta/health       │  │  • /quran/token/{id}   │         │
│  │  • /meta/info         │  │  • /quran/tokens       │         │
│  └───────────────────────┘  │  • /quran/verse/{s}/{a}│         │
│                              │  • /quran/root/{root}  │         │
│                              │  • /quran/search       │         │
│                              │  • /quran/stats        │         │
│                              └────────────┬───────────┘         │
└─────────────────────────────────────────────┼───────────────────┘
                                              │
                                              │ Dependency Injection
                                              │
┌─────────────────────────────────────────────▼───────────────────┐
│                      SERVICE LAYER                               │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ tokenizer_service   │  │  root_extractor                 │  │
│  │  • tokenize_verse() │  │   • QuranCorpusExtractor       │  │
│  │  • normalize_text() │  │   • TanzilExtractor            │  │
│  │  • tokenize_file()  │  │   • AlmaanyExtractor           │  │
│  └─────────────────────┘  │   • Multi-source extraction    │  │
│                            │   • Caching                     │  │
│  ┌─────────────────────┐  └─────────────────────────────────┘  │
│  │ discrepancy_checker │  ┌─────────────────────────────────┐  │
│  │  • check_conflict() │  │  reference_linker               │  │
│  │  • analyze_batch()  │  │   • build_root_index()         │  │
│  │  • get_statistics() │  │   • build_references()         │  │
│  └─────────────────────┘  │   • compress_references()      │  │
│                            └─────────────────────────────────┘  │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      │ ORM Operations
                                      │
┌─────────────────────────────────────▼───────────────────────────┐
│                    DATA ACCESS LAYER (SQLAlchemy)                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  db.py - Database Configuration                          │   │
│  │    • Async Engine (FastAPI)                              │   │
│  │    • Sync Engine (Scripts)                               │   │
│  │    • Session Management                                  │   │
│  │    • Connection Pooling                                  │   │
│  └────────┬──────────────────────────┬──────────────────────┘   │
│           │                          │                           │
│  ┌────────▼──────────┐    ┌─────────▼──────────┐               │
│  │  Token Model      │    │  Root Model         │               │
│  │  • id             │    │  • id               │               │
│  │  • sura           │    │  • root (unique)    │               │
│  │  • aya            │    │  • meaning          │               │
│  │  • position       │    │  • tokens (JSON)    │               │
│  │  • text_ar        │    │  • token_count      │               │
│  │  • normalized     │    │  • metadata_        │               │
│  │  • root           │    └─────────────────────┘               │
│  │  • root_sources   │                                          │
│  │  • status         │                                          │
│  │  • references     │                                          │
│  │  • interpretations│                                          │
│  └───────────────────┘                                          │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      │ SQL Queries
                                      │
┌─────────────────────────────────────▼───────────────────────────┐
│                      DATABASE LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SQLite (Development)  /  PostgreSQL (Production)        │   │
│  │    • tokens table                                         │   │
│  │    • roots table                                          │   │
│  │    • Indexes: sura, aya, root, status                    │   │
│  │    • Foreign keys enabled                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────┐
│                      OFFLINE PIPELINE                            │
│                                                                  │
│  ┌────────────────┐                                             │
│  │ Input Data     │                                             │
│  │ quran_text.txt │                                             │
│  └───────┬────────┘                                             │
│          │                                                       │
│          ▼                                                       │
│  ┌────────────────────────────────────────┐                    │
│  │ 1. tokenize_quran.py                   │                    │
│  │    • Read text file                    │                    │
│  │    • Split by word                     │                    │
│  │    • Normalize Arabic                  │                    │
│  │    • Generate CSV                      │                    │
│  │    • Save to database                  │                    │
│  └─────────────────┬──────────────────────┘                    │
│                    │                                             │
│                    ▼                                             │
│  ┌────────────────────────────────────────┐                    │
│  │ 2. fetch_roots.py                      │                    │
│  │    • Query QuranCorpus API             │                    │
│  │    • Query Tanzil API                  │                    │
│  │    • Query Almaany API                 │                    │
│  │    • Parallel processing               │                    │
│  │    • Cache results (JSON)              │                    │
│  └─────────────────┬──────────────────────┘                    │
│                    │                                             │
│                    ▼                                             │
│  ┌────────────────────────────────────────┐                    │
│  │ 3. reconcile_roots.py                  │                    │
│  │    • Compare sources                   │                    │
│  │    • Detect conflicts                  │                    │
│  │    • Calculate confidence              │                    │
│  │    • Set consensus root                │                    │
│  │    • Update status                     │                    │
│  └─────────────────┬──────────────────────┘                    │
│                    │                                             │
│                    ▼                                             │
│  ┌────────────────────────────────────────┐                    │
│  │ 4. index_references.py                 │                    │
│  │    • Group by root                     │                    │
│  │    • Build reverse index               │                    │
│  │    • Create references                 │                    │
│  │    • Update Root table                 │                    │
│  │    • Compress large groups             │                    │
│  └────────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Tokenization Flow
```
Input Text File
    │
    ├─► Parse line (sura|aya|text)
    │
    ├─► Split into words
    │
    ├─► For each word:
    │   ├─► Store original (text_ar)
    │   ├─► Normalize (remove diacritics)
    │   └─► Track position
    │
    ├─► Write to CSV
    │
    └─► Save to Database (Token table)
```

### 2. Root Extraction Flow
```
Token (normalized word)
    │
    ├─► Check cache
    │   ├─► Hit: Return cached result
    │   └─► Miss: Continue
    │
    ├─► Query sources in parallel:
    │   ├─► QuranCorpus API
    │   ├─► Tanzil API
    │   └─► Almaany API
    │
    ├─► Collect results
    │
    ├─► Store in cache (JSON)
    │
    └─► Update Token.root_sources (JSON)
```

### 3. Discrepancy Resolution Flow
```
Token with multiple root sources
    │
    ├─► Count occurrences of each root
    │
    ├─► Calculate confidence score
    │
    ├─► Determine status:
    │   ├─► All agree + min sources → verified
    │   ├─► Majority + high confidence → verified
    │   ├─► Conflict + low confidence → manual_review
    │   └─► Conflict + moderate → discrepancy
    │
    ├─► Set consensus root
    │
    └─► Update Token.root and Token.status
```

### 4. Reference Building Flow
```
All Tokens with verified roots
    │
    ├─► Group by root
    │   └─► {root: [token_id1, token_id2, ...]}
    │
    ├─► For each token:
    │   └─► references = all other tokens with same root
    │
    ├─► Compress if > max_references
    │
    ├─► Update Token.references (JSON)
    │
    └─► Create/Update Root table entries
```

### 5. API Request Flow
```
HTTP Request
    │
    ├─► FastAPI Router
    │
    ├─► Dependency Injection (DB session)
    │
    ├─► Route Handler
    │   ├─► Validate input (Pydantic)
    │   ├─► Query database (SQLAlchemy)
    │   └─► Transform to response model
    │
    ├─► Serialize to JSON
    │
    └─► HTTP Response
```

## Component Interactions

### Backend Module Dependencies
```
main.py
  ├─► config.py (Settings)
  ├─► db.py (Database)
  └─► api/
      ├─► routes_meta.py
      └─► routes_quran.py
          ├─► models/ (Token, Root)
          └─► db.py (get_db_session)

scripts/
  ├─► tokenize_quran.py
  │   ├─► services/tokenizer_service.py
  │   ├─► models/token_model.py
  │   └─► db.py
  │
  ├─► fetch_roots.py
  │   ├─► services/root_extractor.py
  │   └─► models/token_model.py
  │
  ├─► reconcile_roots.py
  │   ├─► services/discrepancy_checker.py
  │   └─► models/token_model.py
  │
  └─► index_references.py
      ├─► services/reference_linker.py
      └─► models/ (Token, Root)
```

## Async vs Sync Operations

### Async Operations (FastAPI)
- API route handlers
- Database queries (AsyncSession)
- Root extraction (parallel HTTP requests)
- Response streaming (if needed)

### Sync Operations (Scripts)
- File I/O (tokenization)
- CSV generation
- Batch database updates
- Cache file operations

## Security Considerations

### Current Implementation
- Input validation (Pydantic)
- SQL injection protection (SQLAlchemy ORM)
- CORS enabled (configurable)
- Type safety (mypy)

### Production Enhancements (Future)
- Authentication (JWT tokens)
- Rate limiting
- API keys for external services
- Encrypted database connections
- HTTPS/TLS

## Scalability Considerations

### Current Design
- Async support for concurrent requests
- Database connection pooling
- Indexed queries
- Pagination for large result sets
- Reference compression

### Production Scaling (Future)
- Horizontal scaling (multiple FastAPI instances)
- Database read replicas
- Redis for caching
- CDN for static assets
- Load balancing

## Error Handling

### API Layer
- HTTP status codes (4xx, 5xx)
- Pydantic validation errors
- Custom exception handlers
- Detailed error messages (dev)
- Generic messages (production)

### Service Layer
- Try/except blocks
- Graceful degradation
- Logging
- Result objects (success/failure)

### Database Layer
- Connection retry logic
- Transaction rollback
- Foreign key constraints
- Unique constraint handling

## Configuration Management

### Environment Variables (.env)
```
Database: DATABASE_URL
API: API_HOST, API_PORT, API_RELOAD
Paths: QURAN_DATA_PATH, OUTPUT_CSV_PATH
Sources: ROOT_SOURCES
Cache: ROOT_CACHE_PATH
Logging: LOG_LEVEL
```

### Config Loading
```
config.py
  ├─► Load .env file
  ├─► Parse with pydantic-settings
  ├─► Validate types
  ├─► Provide defaults
  └─► Cache with @lru_cache
```

## Testing Strategy

### Unit Tests
- Service layer (tokenization, extraction)
- Model validation
- Utility functions

### Integration Tests
- API endpoints
- Database operations
- End-to-end workflows

### Test Organization
```
tests/
  ├─► test_tokenization.py
  ├─► test_root_extraction.py (future)
  ├─► test_api.py (future)
  └─► test_models.py (future)
```

---

This architecture provides:
- **Separation of concerns** (API, Service, Data layers)
- **Modularity** (pluggable components)
- **Type safety** (full type hints)
- **Scalability** (async support, efficient queries)
- **Maintainability** (clear structure, documentation)
