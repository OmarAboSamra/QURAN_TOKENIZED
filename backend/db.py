"""
Database connection and session management.

This module provides singleton database engines and session factories for both
synchronous (offline scripts) and asynchronous (FastAPI routes) usage.

Architecture:
    - SQLAlchemy 2.0 style with mapped_column and type-annotated models
    - Singleton pattern: engines and session factories are created once and reused
    - Dual mode: sync engine for scripts, async engine for the API server
    - Auto-detects SQLite vs PostgreSQL from DATABASE_URL and applies
      dialect-specific settings (e.g., SQLite PRAGMA foreign_keys=ON)

Usage in FastAPI routes:
    async def my_endpoint(db: AsyncSession = Depends(get_db_session)):
        ...

Usage in offline scripts:
    SessionMaker = get_sync_session_maker()
    with SessionMaker() as session:
        ...
"""
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings

# Load settings once at module level (cached by @lru_cache in config.py)
settings = get_settings()


class Base(DeclarativeBase):
    """
    Base class for all ORM models (Token, Root, Verse).
    
    All models inherit from this to register with SQLAlchemy's metadata,
    which enables automatic table creation via Base.metadata.create_all().
    """

    pass


# ── Singleton caches ──────────────────────────────────────────────
# These are lazily initialized on first access and reused for all
# subsequent calls, ensuring a single connection pool per process.
_sync_engine: Any | None = None
_async_engine: Any | None = None
_sync_session_factory: sessionmaker[Session] | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_sync_engine() -> Any:
    """
    Return (and lazily create) the synchronous database engine singleton.
    
    Used by offline scripts (tokenize_quran.py, extract_roots_all.py, etc.)
    that run outside the async event loop.
    
    For SQLite: disables thread-check and enables foreign key enforcement.
    For PostgreSQL: enables pool_pre_ping to handle stale connections.
    """
    global _sync_engine
    if _sync_engine is not None:
        return _sync_engine

    db_url = settings.database_url

    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            # SQLite by default rejects usage from multiple threads;
            # we disable that since SQLAlchemy manages its own pool
            connect_args={"check_same_thread": False},
            echo=settings.log_level == "DEBUG",
        )

        # SQLite does not enforce foreign keys by default —
        # we enable it on every new connection
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        engine = create_engine(
            db_url,
            echo=settings.log_level == "DEBUG",
            # pool_pre_ping sends a lightweight query before reusing a
            # connection, avoiding errors from connections that timed out
            pool_pre_ping=True,
        )

    _sync_engine = engine
    return _sync_engine


def get_sync_session_maker() -> sessionmaker[Session]:
    """
    Return (and lazily create) the synchronous session maker singleton.
    
    Returns a factory — call it to create individual sessions:
        SessionMaker = get_sync_session_maker()
        with SessionMaker() as session:
            session.query(Token).all()
    """
    global _sync_session_factory
    if _sync_session_factory is not None:
        return _sync_session_factory

    _sync_session_factory = sessionmaker(
        bind=get_sync_engine(), autocommit=False, autoflush=False,
    )
    return _sync_session_factory


def get_async_engine() -> Any:
    """
    Return (and lazily create) the asynchronous database engine singleton.
    
    Used by the FastAPI server for non-blocking database I/O.
    
    Automatically converts the DATABASE_URL to an async dialect:
        sqlite:///  →  sqlite+aiosqlite:///
        postgresql://  →  postgresql+asyncpg://
    """
    global _async_engine
    if _async_engine is not None:
        return _async_engine

    db_url = settings.database_url

    # Convert synchronous URLs to their async driver equivalents
    if db_url.startswith("sqlite"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    _async_engine = create_async_engine(
        db_url,
        echo=settings.log_level == "DEBUG",
        future=True,
    )
    return _async_engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Return (and lazily create) the asynchronous session maker singleton.
    
    expire_on_commit=False prevents attributes from being expired after
    commit, which would cause lazy-load errors in an async context.
    """
    global _async_session_factory
    if _async_session_factory is not None:
        return _async_session_factory

    _async_session_factory = async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    
    Usage in route handlers:
        @router.get("/tokens")
        async def get_tokens(db: AsyncSession = Depends(get_db_session)):
            ...
    
    The session is automatically closed when the request finishes.
    """
    async_session = get_async_session_maker()
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db() -> None:
    """
    Create all database tables from ORM model definitions (synchronous).
    
    Safe to call multiple times — SQLAlchemy only creates tables that
    don't already exist (CREATE TABLE IF NOT EXISTS).
    """
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)


async def init_db_async() -> None:
    """
    Create all database tables from ORM model definitions (async).
    
    Called during FastAPI startup via the lifespan handler in main.py.
    """
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
