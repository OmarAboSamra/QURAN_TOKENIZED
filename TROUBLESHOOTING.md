# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Issue: `pip install` fails with "could not be resolved"

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**
1. Upgrade pip:
   ```powershell
   python -m pip install --upgrade pip
   ```

2. Use specific index:
   ```powershell
   pip install -r requirements.txt --index-url https://pypi.org/simple
   ```

3. Install packages individually:
   ```powershell
   pip install fastapi uvicorn sqlalchemy pydantic
   ```

#### Issue: Virtual environment activation fails

**Symptoms:**
```
.\venv\Scripts\Activate.ps1 : cannot be loaded because running scripts is disabled
```

**Solution:**
Enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again:
```powershell
.\venv\Scripts\Activate.ps1
```

---

### Database Issues

#### Issue: Database file not found

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

**Solutions:**
1. Ensure you're in the project root directory:
   ```powershell
   cd c:\quran-backend
   ```

2. Check DATABASE_URL in `.env`:
   ```env
   DATABASE_URL=sqlite:///./quran.db
   ```

3. Run tokenization to create database:
   ```powershell
   python scripts/tokenize_quran.py --save-to-db
   ```

#### Issue: Database is locked

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**
1. Close other connections to the database
2. Restart the API server
3. Delete `quran.db` and re-run tokenization

#### Issue: Migration errors with PostgreSQL

**Symptoms:**
```
relation "tokens" already exists
```

**Solutions:**
1. Drop and recreate the database:
   ```sql
   DROP DATABASE quran_db;
   CREATE DATABASE quran_db;
   ```

2. Or drop specific tables:
   ```sql
   DROP TABLE IF EXISTS tokens CASCADE;
   DROP TABLE IF EXISTS roots CASCADE;
   ```

3. Re-run tokenization

---

### Tokenization Issues

#### Issue: Input file not found

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: './data/quran_original_text.txt'
```

**Solutions:**
1. Check the file exists:
   ```powershell
   Test-Path data\quran_original_text.txt
   ```

2. Create sample file if missing:
   ```powershell
   # File already exists in the repo
   # If missing, download Qur'an text from tanzil.net
   ```

3. Specify custom path:
   ```powershell
   python scripts/tokenize_quran.py --input path\to\quran.txt
   ```

#### Issue: Parsing errors (invalid format)

**Symptoms:**
```
Warning: Could not parse line 42: ...
```

**Solutions:**
1. Check file format is `sura|aya|text` or `sura:aya text`

2. Example valid formats:
   ```
   1|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ
   1:1 بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ
   ```

3. Remove comments (lines starting with #)

4. Check encoding is UTF-8

#### Issue: Arabic text appears garbled

**Symptoms:**
```
Tokens saved but text looks like: ????????
```

**Solutions:**
1. Ensure file is UTF-8 encoded:
   ```powershell
   # In VS Code: File -> Save with Encoding -> UTF-8
   ```

2. Check terminal supports UTF-8:
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

---

### API Server Issues

#### Issue: Port already in use

**Symptoms:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Solutions:**
1. Use different port in `.env`:
   ```env
   API_PORT=8001
   ```

2. Or kill process using port 8000:
   ```powershell
   # Find process
   netstat -ano | findstr :8000
   
   # Kill process (replace PID with actual process ID)
   taskkill /PID <PID> /F
   ```

#### Issue: Import errors when starting server

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**
1. Ensure virtual environment is activated:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. Verify with:
   ```powershell
   pip list | findstr fastapi
   ```

3. Reinstall if missing:
   ```powershell
   pip install fastapi uvicorn
   ```

#### Issue: 404 errors for valid endpoints

**Symptoms:**
```
{"detail":"Not Found"}
```

**Solutions:**
1. Check URL is correct:
   - Correct: `http://localhost:8000/quran/verse/1/1`
   - Wrong: `http://localhost:8000/verse/1/1`

2. Verify server started successfully (check console output)

3. Check API docs: http://localhost:8000/docs

#### Issue: Database errors in API responses

**Symptoms:**
```
{"detail":"Internal Server Error"}
```

**Solutions:**
1. Check server logs in console

2. Ensure database is initialized:
   ```powershell
   python scripts/tokenize_quran.py --save-to-db
   ```

3. Check LOG_LEVEL in `.env`:
   ```env
   LOG_LEVEL=DEBUG
   ```

4. Restart server and retry

---

### Root Extraction Issues

#### Issue: All extractions fail

**Symptoms:**
```
Not implemented yet
```

**Solution:**
This is expected! Root extraction sources are placeholders.

To implement:
1. Edit `backend/services/root_extractor_v2.py`
2. Add actual API calls or web scraping
3. See `README.md` for examples

#### Issue: Cache file errors

**Symptoms:**
```
Warning: Could not save cache: ...
```

**Solutions:**
1. Ensure `data/` directory exists:
   ```powershell
   mkdir data -Force
   ```

2. Check file permissions

3. Verify path in `.env`:
   ```env
   ROOT_CACHE_PATH=./data/quran_roots_cache.json
   ```

---

### Type Checking Issues

#### Issue: mypy errors

**Symptoms:**
```
error: Incompatible types in assignment
```

**Solutions:**
1. Install type stubs:
   ```powershell
   pip install types-all
   ```

2. Skip type checking temporarily:
   ```python
   # type: ignore
   ```

3. Fix actual type issues (preferred)

---

### Testing Issues

#### Issue: pytest not found

**Symptoms:**
```
'pytest' is not recognized as an internal or external command
```

**Solutions:**
1. Install pytest:
   ```powershell
   pip install pytest pytest-asyncio
   ```

2. Run with python:
   ```powershell
   python -m pytest tests/
   ```

#### Issue: Test imports fail

**Symptoms:**
```
ModuleNotFoundError: No module named 'backend'
```

**Solutions:**
1. Ensure you're in project root:
   ```powershell
   cd c:\quran-backend
   ```

2. Add to PYTHONPATH:
   ```powershell
   $env:PYTHONPATH = "."
   pytest tests/
   ```

---

### Performance Issues

#### Issue: Slow tokenization

**Symptoms:**
Takes very long to tokenize large files

**Solutions:**
1. Use faster regex compilation (already implemented)
2. Process in batches
3. Use PyPy instead of CPython (advanced)

#### Issue: Slow API responses

**Symptoms:**
Requests take > 1 second

**Solutions:**
1. Check database indexes are created:
   ```python
   # Indexes already defined in models
   # Verify with: SELECT * FROM sqlite_master WHERE type='index';
   ```

2. Use pagination for large results:
   ```
   /quran/tokens?page=1&page_size=50
   ```

3. Switch to PostgreSQL for better performance

4. Add caching layer (Redis)

---

### Data Issues

#### Issue: Missing verses

**Symptoms:**
Query returns 404 for valid verse reference

**Solutions:**
1. Check verse exists in input file

2. Verify tokenization completed:
   ```powershell
   python scripts/tokenize_quran.py
   ```

3. Query database directly:
   ```powershell
   sqlite3 quran.db "SELECT * FROM tokens WHERE sura=1 AND aya=1;"
   ```

#### Issue: Duplicate tokens

**Symptoms:**
Same token appears multiple times

**Solutions:**
1. Check unique constraint in database:
   ```sql
   -- Should have unique index on (sura, aya, position)
   ```

2. Re-run tokenization with clean database:
   ```powershell
   rm quran.db
   python scripts/tokenize_quran.py --save-to-db
   ```

---

### Configuration Issues

#### Issue: .env file not loaded

**Symptoms:**
Using default values instead of custom config

**Solutions:**
1. Ensure `.env` file exists in project root:
   ```powershell
   Test-Path .env
   ```

2. Check file name (not `.env.txt`)

3. Verify format:
   ```env
   # Correct
   API_PORT=8000
   
   # Wrong
   API_PORT = 8000
   ```

4. Restart server after changes

#### Issue: Invalid configuration values

**Symptoms:**
```
ValidationError: 1 validation error for Settings
```

**Solutions:**
1. Check data types match:
   ```env
   API_PORT=8000    # Number, not "8000"
   API_RELOAD=true  # Boolean, not "yes"
   ```

2. See `.env.example` for correct format

---

## Debugging Tips

### Enable Debug Logging

In `.env`:
```env
LOG_LEVEL=DEBUG
```

### Use Interactive Python

```powershell
python
>>> from backend.models import Token
>>> from backend.db import get_sync_session_maker
>>> SessionMaker = get_sync_session_maker()
>>> with SessionMaker() as session:
...     tokens = session.query(Token).limit(5).all()
...     print(tokens)
```

### Check Database Schema

```powershell
sqlite3 quran.db
.schema tokens
.schema roots
```

### View SQL Queries

Set in `.env`:
```env
LOG_LEVEL=DEBUG
```

SQLAlchemy will print all queries.

### Test API with curl

```powershell
# Health check
curl http://localhost:8000/meta/health

# Get verse
curl http://localhost:8000/quran/verse/1/1

# Search
curl "http://localhost:8000/quran/search?q=الله"

# With verbose output
curl -v http://localhost:8000/meta/health
```

---

## Getting Help

### Resources

1. **Documentation**
   - README.md - Complete guide
   - QUICKSTART.md - Quick setup
   - ARCHITECTURE.md - System design
   - PROJECT_SUMMARY.md - Overview

2. **Code**
   - All code is type-hinted
   - Docstrings on all functions
   - Inline comments for complex logic

3. **API Documentation**
   - Interactive: http://localhost:8000/docs
   - Alternative: http://localhost:8000/redoc

### Still Stuck?

1. Check all files are in correct locations
2. Verify virtual environment is activated
3. Ensure all dependencies installed
4. Try deleting `quran.db` and re-running
5. Check Python version is 3.10+

### Quick Reset

Nuclear option - start fresh:

```powershell
# Delete virtual environment
rm -r venv

# Delete database
rm quran.db

# Delete cache
rm data\quran_tokens_word.csv
rm data\quran_roots_cache.json

# Start over
.\setup_and_run.ps1
```

---

## Common Workflow Issues

### "I ran tokenization but API returns empty"

Check:
1. Used `--save-to-db` flag?
   ```powershell
   python scripts/tokenize_quran.py --save-to-db
   ```

2. Database exists?
   ```powershell
   Test-Path quran.db
   ```

3. Restart API server after tokenization

### "Root extraction doesn't work"

Expected! Implement in `backend/services/root_extractor_v2.py`:
```python
async def extract_root(self, word: str) -> RootExtractionResult:
    # Add your implementation here
    # Example: call API, parse response, return result
    pass
```

### "Changes to code don't appear"

1. Check `API_RELOAD=true` in `.env`
2. Restart server manually
3. Check you're editing correct file
4. Verify virtual environment is activated

---

**Remember**: Most issues are environment-related. When in doubt, recreate the virtual environment and reinstall dependencies.
