"""
FastAPI application entry point.

This is the main FastAPI application that provides REST APIs for:
- Token retrieval and search (GET /quran/token, /quran/tokens, /quran/search)
- Root lookup and analysis (GET /quran/root/{root})
- Verse reconstruction from tokens (GET /quran/verse/{sura}/{aya})
- Statistics and metadata (GET /quran/stats, /meta/health, /meta/info)
- Background pipeline jobs via Celery (POST /pipeline/tokenize, etc.)

The application is structured as:
    main.py          → App creation, middleware, lifespan (this file)
    api/             → Route handlers grouped by domain
    models/          → SQLAlchemy ORM models (Token, Root, Verse)
    repositories/    → Database query layer
    services/        → Business logic (tokenizer, root extractor, etc.)
    tasks/           → Celery background tasks

Usage:
    python backend/main.py          # Direct run
    uvicorn backend.main:app --reload  # Development with auto-reload
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api import routes_meta, routes_quran_enhanced, routes_pipeline
from backend.config import get_settings
from backend.db import get_async_engine, init_db_async


async def _ensure_fts5() -> None:
    """
    Create the FTS5 virtual table and sync triggers if they don't exist.

    This is a no-op when they already exist thanks to IF NOT EXISTS.
    Called once during startup for SQLite databases.
    """
    from sqlalchemy import text

    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS tokens_fts "
            "USING fts5(text_ar, normalized, content='tokens', "
            "content_rowid='id', tokenize='unicode61')"
        ))
        await conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS tokens_fts_insert "
            "AFTER INSERT ON tokens BEGIN "
            "INSERT INTO tokens_fts(rowid, text_ar, normalized) "
            "VALUES (new.id, new.text_ar, new.normalized); END;"
        ))
        await conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS tokens_fts_delete "
            "AFTER DELETE ON tokens BEGIN "
            "INSERT INTO tokens_fts(tokens_fts, rowid, text_ar, normalized) "
            "VALUES ('delete', old.id, old.text_ar, old.normalized); END;"
        ))
        await conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS tokens_fts_update "
            "AFTER UPDATE ON tokens BEGIN "
            "INSERT INTO tokens_fts(tokens_fts, rowid, text_ar, normalized) "
            "VALUES ('delete', old.id, old.text_ar, old.normalized); "
            "INSERT INTO tokens_fts(rowid, text_ar, normalized) "
            "VALUES (new.id, new.text_ar, new.normalized); END;"
        ))
        # Rebuild to ensure index is populated from existing data
        await conn.execute(text(
            "INSERT INTO tokens_fts(tokens_fts) VALUES('rebuild')"
        ))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event handler for FastAPI.
    
    Runs once on startup (before first request) and once on shutdown.
    Startup: creates database tables if they don't exist.
    Shutdown: placeholder for cleanup (closing pools, flushing caches).
    
    """
    # Startup
    from backend.logging_config import configure_logging
    configure_logging()

    settings = get_settings()
    print("=" * 60)
    print(f"{settings.api_title} v{settings.api_version}")
    print("=" * 60)
    print("Initializing database...")
    
    try:
        await init_db_async()
        print("[OK] Database initialized")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")

    # Create FTS5 full-text index if it doesn't exist (SQLite only)
    if settings.is_sqlite:
        try:
            await _ensure_fts5()
            print("[OK] FTS5 search index ready")
        except Exception as e:
            print(f"Warning: FTS5 setup skipped: {e}")
    
    print(f"[OK] Server starting on http://{settings.api_host}:{settings.api_port}")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("Shutting down...")


# ── Application factory ──────────────────────────────────────────
# The app object is created at module level so that uvicorn can
# import it directly as "backend.main:app".
settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "Production-ready backend for Qur'an analysis with tokenization, "
        "root extraction, and reference linking."
    ),
    lifespan=lifespan,
)

# ── CORS middleware ───────────────────────────────────────────────
# Uses the comma-separated CORS_ORIGINS env var (default: "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics ────────────────────────────────────────────
if settings.prometheus_enabled:
    from backend.metrics import get_instrumentator
    _instrumentator = get_instrumentator()
    _instrumentator.instrument(app)
    _instrumentator.expose(app, endpoint="/metrics")

# ── Router registration ──────────────────────────────────────────
# /meta/*    → Health checks and API info
# /quran/*   → Core Qur'an data endpoints (tokens, verses, roots, search)
# /pipeline/* → Background job management (Celery integration)
app.include_router(routes_meta.router)
app.include_router(routes_quran_enhanced.router)
app.include_router(routes_pipeline.router)

# ── Global exception handler for database errors (C5) ────────────
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.logging_config import get_logger

_logger = get_logger("backend.main")


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request, exc: SQLAlchemyError):
    """Return 503 instead of a raw 500 stack trace on DB errors."""
    _logger.error("db_error", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable — please try again later"},
    )


# ── Static files ─────────────────────────────────────────────────
# Serves the interactive demo frontend at /static/demo/index.html
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.api_title}",
        "version": settings.api_version,
        "docs": "/docs",
        "demo": "/demo",
        "health": "/meta/health",
        "pipeline": "/pipeline/status",
    }


@app.get("/demo")
async def demo() -> FileResponse:
    """Serve the demo frontend."""
    demo_path = Path(__file__).parent / "static" / "demo" / "index.html"
    return FileResponse(demo_path)


@app.get("/demo-enhanced")
async def demo_enhanced() -> FileResponse:
    """Redirect legacy /demo-enhanced to /demo."""
    demo_path = Path(__file__).parent / "static" / "demo" / "index.html"
    return FileResponse(demo_path)


def main() -> None:
    """Run the application using uvicorn."""
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
