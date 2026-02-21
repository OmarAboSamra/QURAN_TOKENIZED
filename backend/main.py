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
from backend.db import init_db_async


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event handler for FastAPI.
    
    Runs once on startup (before first request) and once on shutdown.
    Startup: creates database tables if they don't exist.
    Shutdown: placeholder for cleanup (closing pools, flushing caches).
    
    NOTE: configure_logging() from logging_config.py and the Prometheus
    instrumentator from metrics.py are NOT wired here yet — these are
    known gaps flagged for the next optimization pass.
    """
    # Startup
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
# Currently allows ALL origins for local development convenience.
# TODO: use settings.cors_origins_list for production deployments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production via config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router registration ──────────────────────────────────────────
# /meta/*    → Health checks and API info
# /quran/*   → Core Qur'an data endpoints (tokens, verses, roots, search)
# /pipeline/* → Background job management (Celery integration)
app.include_router(routes_meta.router)
app.include_router(routes_quran_enhanced.router)
app.include_router(routes_pipeline.router)

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
