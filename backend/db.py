"""Database connection and session management."""
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ── Singleton caches ──────────────────────────────────────────────
_sync_engine: Any | None = None
_async_engine: Any | None = None
_sync_session_factory: sessionmaker[Session] | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


# Synchronous engine for offline scripts
def get_sync_engine() -> Any:
    """Return (and lazily create) the synchronous database engine singleton."""
    global _sync_engine
    if _sync_engine is not None:
        return _sync_engine

    db_url = settings.database_url

    # SQLite-specific configuration
    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=settings.log_level == "DEBUG",
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        engine = create_engine(
            db_url,
            echo=settings.log_level == "DEBUG",
            pool_pre_ping=True,
        )

    _sync_engine = engine
    return _sync_engine


def get_sync_session_maker() -> sessionmaker[Session]:
    """Return (and lazily create) the synchronous session maker singleton."""
    global _sync_session_factory
    if _sync_session_factory is not None:
        return _sync_session_factory

    _sync_session_factory = sessionmaker(
        bind=get_sync_engine(), autocommit=False, autoflush=False,
    )
    return _sync_session_factory


# Asynchronous engine for FastAPI
def get_async_engine() -> Any:
    """Return (and lazily create) the asynchronous database engine singleton."""
    global _async_engine
    if _async_engine is not None:
        return _async_engine

    db_url = settings.database_url

    # Convert SQLite URL to async
    if db_url.startswith("sqlite"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
    # Convert PostgreSQL URL to async
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    _async_engine = create_async_engine(
        db_url,
        echo=settings.log_level == "DEBUG",
        future=True,
    )
    return _async_engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return (and lazily create) the asynchronous session maker singleton."""
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


# Dependency for FastAPI routes
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for FastAPI dependency injection."""
    async_session = get_async_session_maker()
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db() -> None:
    """Initialize database tables (for synchronous usage)."""
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)


async def init_db_async() -> None:
    """Initialize database tables (for asynchronous usage)."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
