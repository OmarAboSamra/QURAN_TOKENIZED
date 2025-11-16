"""
FastAPI application entry point.

This is the main FastAPI application that provides REST APIs for:
- Token retrieval and search
- Root lookup and analysis
- Verse reconstruction
- Statistics and metadata

Usage:
    python backend/main.py
    or
    uvicorn backend.main:app --reload
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api import routes_meta, routes_quran, routes_quran_enhanced, routes_pipeline
from backend.config import get_settings
from backend.db import init_db_async


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event handler for FastAPI.
    
    This function runs on startup and shutdown to initialize
    and cleanup resources.
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


# Create FastAPI application
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_meta.router)
app.include_router(routes_quran_enhanced.router)
app.include_router(routes_quran.router)
app.include_router(routes_pipeline.router)

# Mount static files for demo
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
        "demo_enhanced": "/demo-enhanced",
        "health": "/meta/health",
        "pipeline": "/pipeline/status",
    }


@app.get("/demo")
async def demo() -> FileResponse:
    """Serve the React demo frontend."""
    demo_path = Path(__file__).parent / "static" / "demo" / "index.html"
    return FileResponse(demo_path)


@app.get("/demo-enhanced")
async def demo_enhanced() -> FileResponse:
    """Serve the enhanced React demo with components and caching."""
    demo_path = Path(__file__).parent / "static" / "demo" / "index-enhanced.html"
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
