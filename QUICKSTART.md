# Quick Start Guide

## Installation (5 minutes)

### 1. Set Up Virtual Environment

```powershell
# Navigate to project directory
cd c:\quran-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Environment

```powershell
# Environment file already created (.env)
# Default uses SQLite - no additional setup needed
```

### 3. Run Tokenization

```powershell
# Tokenize sample data and save to database
python scripts/tokenize_quran.py --save-to-db
```

**Expected output**:
```
✓ Successfully tokenized 82 words
✓ CSV output written to: .\data\quran_tokens_word.csv
✓ Saved 82 tokens to database
```

### 4. Start API Server

```powershell
# Start FastAPI server
python backend/main.py
```

**Expected output**:
```
============================================================
Qur'an Analysis API v0.1.0
============================================================
✓ Database initialized
✓ Server starting on http://0.0.0.0:8000
```

### 5. Test the API

Open a new terminal and test:

```powershell
# Health check
curl http://localhost:8000/meta/health

# Get verse 1:1 (Bismillah)
curl http://localhost:8000/quran/verse/1/1

# Get statistics
curl http://localhost:8000/quran/stats

# Search for "الله"
curl "http://localhost:8000/quran/search?q=الله"
```

Or visit in browser:
- Interactive API Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## Next Steps

### Add Complete Qur'an Data

The sample data only includes Al-Fatiha and first few verses of Al-Baqarah.

**To add complete Qur'an**:

1. Download from Tanzil: https://tanzil.net/download/
2. Convert to format: `sura|aya|text`
3. Save to `data/quran_original_text.txt`
4. Re-run tokenization:
   ```powershell
   python scripts/tokenize_quran.py --save-to-db
   ```

### Implement Root Extraction

Current root extractors are placeholders.

**To implement**:

1. Open `backend/services/root_extractor.py`
2. Implement API calls in each extractor class:
   - `QuranCorpusExtractor`
   - `TanzilExtractor`
   - `AlmaanyExtractor`
3. Run extraction:
   ```powershell
   python scripts/fetch_roots.py
   ```
4. Reconcile results:
   ```powershell
   python scripts/reconcile_roots.py
   ```
5. Build references:
   ```powershell
   python scripts/index_references.py
   ```

### Deploy to Production

1. **Use PostgreSQL**:
   ```env
   DATABASE_URL=postgresql://user:pass@localhost:5432/quran_db
   ```

2. **Update production settings**:
   ```env
   API_RELOAD=false
   LOG_LEVEL=WARNING
   ```

3. **Run with production server**:
   ```powershell
   pip install gunicorn
   gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

## Common Issues

### Import Errors

If you see import errors, ensure:
1. Virtual environment is activated
2. Dependencies are installed: `pip install -r requirements.txt`

### Database Errors

If database errors occur:
1. Check `.env` file exists
2. Ensure `data/` directory exists
3. Try deleting `quran.db` and re-run tokenization

### Port Already in Use

If port 8000 is in use:
1. Change port in `.env`: `API_PORT=8001`
2. Or stop other process using port 8000

## File Structure Reference

```
quran-backend/
├── backend/           # Main application code
│   ├── main.py       # FastAPI entry point
│   ├── config.py     # Configuration
│   ├── db.py         # Database connection
│   ├── api/          # API routes
│   ├── models/       # ORM models
│   └── services/     # Business logic
├── scripts/          # Offline processing scripts
├── data/             # Data files and output
├── tests/            # Unit tests
└── .env              # Environment configuration
```

## Development Tips

### Type Checking

```powershell
mypy backend/
```

### Code Formatting

```powershell
black backend/ scripts/
```

### Run Tests

```powershell
pytest tests/ -v
```

### Watch Mode for Development

The API server auto-reloads on code changes when `API_RELOAD=true`.

## Support

- Check README.md for full documentation
- Review code comments for implementation details
- All services are fully type-hinted for IDE support

---

**Ready to start!** Run `python backend/main.py` and visit http://localhost:8000/docs
