"""Base repository class for database operations."""
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.db import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.
    
    This generic repository can be extended for specific models
    to add custom query methods.
    """

    def __init__(self, model: type[ModelType]):
        """Initialize repository with model class."""
        self.model = model

    # Synchronous methods for scripts
    def get_by_id(self, session: Session, id: int) -> Optional[ModelType]:
        """Get record by ID."""
        return session.get(self.model, id)

    def get_all(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = session.execute(stmt)
        return list(result.scalars().all())

    def create(self, session: Session, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        session.add(instance)
        session.flush()
        return instance

    def update(
        self,
        session: Session,
        instance: ModelType,
        **kwargs: Any,
    ) -> ModelType:
        """Update an existing record."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        session.flush()
        return instance

    def delete(self, session: Session, id: int) -> bool:
        """Delete a record by ID."""
        stmt = delete(self.model).where(self.model.id == id)
        result = session.execute(stmt)
        return result.rowcount > 0

    def count(self, session: Session) -> int:
        """Count total records."""
        stmt = select(func.count()).select_from(self.model)
        result = session.execute(stmt)
        return result.scalar() or 0

    # Async methods for API endpoints
    async def aget_by_id(
        self,
        session: AsyncSession,
        id: int,
    ) -> Optional[ModelType]:
        """Get record by ID (async)."""
        return await session.get(self.model, id)

    async def aget_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get all records with pagination (async)."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def acreate(self, session: AsyncSession, **kwargs: Any) -> ModelType:
        """Create a new record (async)."""
        instance = self.model(**kwargs)
        session.add(instance)
        await session.flush()
        return instance

    async def aupdate(
        self,
        session: AsyncSession,
        instance: ModelType,
        **kwargs: Any,
    ) -> ModelType:
        """Update an existing record (async)."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await session.flush()
        return instance

    async def adelete(self, session: AsyncSession, id: int) -> bool:
        """Delete a record by ID (async)."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.rowcount > 0

    async def acount(self, session: AsyncSession) -> int:
        """Count total records (async)."""
        stmt = select(func.count()).select_from(self.model)
        result = await session.execute(stmt)
        return result.scalar() or 0

    def _build_query(self, **filters: Any) -> Select:
        """Build base query with optional filters."""
        stmt = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)
        return stmt
