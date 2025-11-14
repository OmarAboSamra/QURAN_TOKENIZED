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


# Synchronous engine for offline scripts
def get_sync_engine() -> Any:
    """Create synchronous database engine."""
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
    
    return engine


def get_sync_session_maker() -> sessionmaker[Session]:
    """Create synchronous session maker."""
    engine = get_sync_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


# Asynchronous engine for FastAPI
def get_async_engine() -> Any:
    """Create asynchronous database engine."""
    db_url = settings.database_url
    
    # Convert SQLite URL to async
    if db_url.startswith("sqlite"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
    # Convert PostgreSQL URL to async
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    return create_async_engine(
        db_url,
        echo=settings.log_level == "DEBUG",
        future=True,
    )


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Create asynchronous session maker."""
    engine = get_async_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


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
