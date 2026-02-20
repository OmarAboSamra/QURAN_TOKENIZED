# Qur'an Analysis Backend

A production-ready Python backend for Qur'an analysis featuring tokenization, root extraction, discrepancy detection, and reference linking.

## 🎯 Features

- **Word-level Tokenization**: Split Qur'an text into individual words with position tracking
- **Arabic Text Normalization**: Remove diacritics and normalize text for consistent analysis
- **Multi-source Root Extraction**: Fetch Arabic roots from multiple online sources
- **Discrepancy Detection**: Compare results across sources and flag conflicts
- **Reference Linking**: Build bidirectional links between words sharing the same root
- **REST API**: FastAPI-based API with full CRUD operations and search
- **Type-safe**: Fully type-hinted codebase for better IDE support and error catching
- **Async Support**: Asynchronous database operations for better performance
- **Extensible**: Modular design allows adding new features (meanings, translations, etc.)

## 📁 Project Structure

```
quran-backend/
│
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management (pydantic-settings)
│   ├── db.py                   # Database engine & session singletons
│   ├── cache.py                # Redis cache manager
│   ├── metrics.py              # Prometheus metrics
│   ├── logging_config.py       # Structured logging (structlog)
│   │
│   ├── api/
│   │   ├── schemas.py              # Shared Pydantic response models
│   │   ├── routes_quran_enhanced.py # Qur'an data endpoints
│   │   ├── routes_meta.py          # Health check and metadata
│   │   └── routes_pipeline.py      # Pipeline management endpoints
│   │
│   ├── models/
│   │   ├── types.py            # Shared SQLAlchemy types (JSONType)
│   │   ├── token_model.py      # Token ORM model
│   │   ├── root_model.py       # Root ORM model
│   │   └── verse_model.py      # Verse ORM model
│   │
│   ├── repositories/
│   │   ├── base.py             # Generic CRUD repository
│   │   └── token_repository.py # Token-specific queries
│   │
│   ├── services/
│   │   ├── tokenizer_service.py      # Tokenization logic
│   │   ├── root_extractor_v2.py      # Multi-source root extraction
│   │   ├── discrepancy_checker.py    # Conflict detection
│   │   └── reference_linker.py       # Reference building
│   │
│   ├── tasks/                  # Celery background tasks
│   └── static/demo/            # Demo frontend
│
├── scripts/
│   ├── tokenize_quran.py       # Offline tokenization script
│   ├── fetch_roots.py          # Root extraction script
│   ├── reconcile_roots.py      # Discrepancy reconciliation
│   └── index_references.py     # Build reference index
│
├── data/
│   ├── quran_original_text.txt      # Input: Qur'an text
│   ├── quran_tokens_word.csv        # Output: Tokenized words
│   └── quran_roots_cache.json       # Cache: Root extraction results
│
├── docs/                       # Technical documentation
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or poetry for package management

### Installation

1. **Clone the repository** (or navigate to the project directory):

```powershell
cd c:\quran-backend
```

2. **Create a virtual environment**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. **Install dependencies**:

```powershell
pip install -r requirements.txt
```

4. **Set up environment variables**:

```powershell
copy .env.example .env
```

Edit `.env` if needed (default uses SQLite):

```env
DATABASE_URL=sqlite:///./quran.db
API_HOST=0.0.0.0
API_PORT=8000
```

### Running the Pipeline

#### Stage 1: Tokenization

Tokenize the Qur'an text into individual words:

```powershell
python scripts/tokenize_quran.py --save-to-db
```

This will:
- Read `data/quran_original_text.txt`
- Generate `data/quran_tokens_word.csv`
- Save tokens to the database (if `--save-to-db` flag is used)

**Output Example**:
```csv
sura,aya,position,text_ar,normalized
1,1,0,بِسْمِ,بسم
1,1,1,ٱللَّهِ,الله
1,1,2,ٱلرَّحْمَٰنِ,الرحمن
```

#### Stage 2: Root Extraction (Placeholder)

Extract Arabic roots from multiple sources:

```powershell
python scripts/fetch_roots.py --limit 100
```

**Note**: Root extraction uses multiple online sources configured in `backend/services/root_extractor_v2.py`.

#### Stage 3: Reconcile Discrepancies

Compare roots from multiple sources and detect conflicts:

```powershell
python scripts/reconcile_roots.py
```

This will:
- Compare roots from different sources
- Set consensus root when sources agree
- Flag discrepancies for manual review

#### Stage 4: Build References

Create bidirectional links between words sharing the same root:

```powershell
python scripts/index_references.py
```

This will:
- Group tokens by root
- Build reference lists
- Update both Token and Root tables

### Running the API Server

Start the FastAPI development server:

```powershell
python backend/main.py
```

Or using uvicorn directly:

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### Metadata

- `GET /` - Welcome message
- `GET /meta/health` - Health check
- `GET /meta/info` - API information

### Qur'an Data

- `GET /quran/token/{token_id}` - Get single token by ID
- `GET /quran/tokens` - List tokens with pagination and filters
  - Query params: `page`, `page_size`, `sura`, `aya`, `root`, `status_filter`
- `GET /quran/verse/{sura}/{aya}` - Get complete verse with all tokens
- `GET /quran/root/{root}` - Get all tokens sharing a root
- `GET /quran/search?q={query}` - Search tokens by Arabic text
- `GET /quran/stats` - Get overall statistics

### Example Requests

```bash
# Get health status
curl http://localhost:8000/meta/health

# Get all tokens from Surah 1
curl "http://localhost:8000/quran/tokens?sura=1"

# Get verse 1:1 (Al-Fatiha, verse 1)
curl http://localhost:8000/quran/verse/1/1

# Search for a word
curl "http://localhost:8000/quran/search?q=الله"

# Get statistics
curl http://localhost:8000/quran/stats
```

## 🗄️ Database Schema

### Token Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| sura | Integer | Surah number (1-114) |
| aya | Integer | Verse number |
| position | Integer | Position within verse |
| text_ar | Text | Original Arabic with diacritics |
| normalized | Text | Normalized without diacritics |
| root | String | Verified Arabic root |
| root_sources | JSON | Roots from each source |
| status | Enum | verified/discrepancy/missing |
| references | JSON | Related token IDs |
| interpretations | JSON | Meanings (future) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### Root Table

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| root | String | Arabic root (unique) |
| meaning | Text | English meaning (optional) |
| tokens | JSON | List of token IDs |
| token_count | Integer | Number of tokens |
| metadata_ | JSON | Additional data |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

## 🔧 Configuration

Environment variables (`.env` file):

```env
# Database
DATABASE_URL=sqlite:///./quran.db
# For PostgreSQL: postgresql://user:password@localhost:5432/quran_db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Data paths
QURAN_DATA_PATH=./data/quran_original_text.txt
OUTPUT_CSV_PATH=./data/quran_tokens_word.csv

# Root extraction
ROOT_SOURCES=qurancorpus,tanzil,almaany
ROOT_CACHE_PATH=./data/quran_roots_cache.json

# Logging
LOG_LEVEL=INFO
```

## 🔄 Pipeline Stages

### Stage 1: Tokenization ✅
**Status**: Implemented and ready to use

Splits Qur'an text into individual words with normalization.

### Stage 2: Root Extraction ✅
**Status**: Multi-source extraction implemented

Extracts roots from multiple sources with consensus verification:
- QuranCorpus (offline cache)
- AlMaany
- Baheth
- PyArabic (algorithmic)
- AlKhalil (algorithmic)

See `backend/services/root_extractor_v2.py` for implementation.

### Stage 3: Discrepancy Detection ✅
**Status**: Fully implemented

Compares roots from multiple sources and flags conflicts.

### Stage 4: Reference Linking ✅
**Status**: Fully implemented

Builds bidirectional references between tokens sharing roots.

### Stage 5: API Service ✅
**Status**: Fully implemented

Production-ready FastAPI with comprehensive endpoints.

## 🧪 Testing

Run tests:

```powershell
pytest tests/
```

With coverage:

```powershell
pytest --cov=backend tests/
```

## 🐘 Using PostgreSQL

To use PostgreSQL instead of SQLite:

1. Install PostgreSQL and create a database:

```sql
CREATE DATABASE quran_db;
CREATE USER quran_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE quran_db TO quran_user;
```

2. Update `.env`:

```env
DATABASE_URL=postgresql://quran_user:your_password@localhost:5432/quran_db
```

3. Install asyncpg (already in requirements.txt):

```powershell
pip install asyncpg
```

## 📝 Adding Qur'an Data

The sample data file includes only a few verses. To get the complete Qur'an:

### Option 1: Tanzil Project

Download from https://tanzil.net/download/

Convert to the required format:
```
sura|aya|text
```

### Option 2: QuranComplex

Download from https://qurancomplex.gov.sa/

### Option 3: Corpus

Use the Quranic Arabic Corpus: https://corpus.quran.com/

## 🛠️ Extending Root Extraction

To add a new root extraction source, edit `backend/services/root_extractor_v2.py`:

```python
class MyExtractor(BaseRootExtractor):
    async def extract_root(self, word: str) -> RootExtractionResult:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}?word={word}"
                )
                root = parse_response(response)
                
                return RootExtractionResult(
                    word=word,
                    root=root,
                    source=self.name,
                    success=True,
                )
        except Exception as e:
            return RootExtractionResult(
                word=word,
                root=None,
                source=self.name,
                success=False,
                error=str(e),
            )
```

## 🚀 Production Deployment

### Using Docker (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```powershell
docker build -t quran-backend .
docker run -p 8000:8000 quran-backend
```

### Environment-specific Settings

For production, update `.env`:

```env
API_RELOAD=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://user:pass@production-db:5432/quran_db
```

## 📈 Future Enhancements

The architecture supports adding:

1. **Meanings/Translations**: Add to `interpretations` field
2. **Tafsir Integration**: Link to commentary sources
3. **Audio Recitations**: Store audio file references
4. **Advanced Search**: Full-text search with Elasticsearch
5. **User Annotations**: Allow users to add notes
6. **Morphological Analysis**: Detailed grammar analysis
7. **Verse Context**: Related verses and themes

## 📚 Resources

- **Tanzil Project**: https://tanzil.net/
- **Quranic Arabic Corpus**: https://corpus.quran.com/
- **QuranComplex**: https://qurancomplex.gov.sa/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with type hints
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is provided as-is for educational and research purposes.

## 👨‍💻 Support

For questions or issues:
1. Check the documentation
2. Review the code comments
3. Open an issue on the repository

---

**Built with**: Python 3.11+ | FastAPI | SQLAlchemy | PostgreSQL/SQLite
