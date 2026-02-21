"""
Token repository with domain-specific query methods.

Extends BaseRepository with queries tailored to the Qur'an analysis
use case: looking up tokens by location (sura/aya/position), by root,
by text search, and finding tokens that still need root extraction.

Like the base class, each method has sync + async variants.
Sync methods are used by offline scripts (tokenize_quran.py, etc.).
Async methods are used by FastAPI route handlers.
"""
from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from backend.models.token_model import Token, TokenStatus
from backend.models.verse_model import Verse
from backend.repositories.base import BaseRepository


class TokenRepository(BaseRepository[Token]):
    """Repository for Token model with custom queries."""

    def __init__(self):
        """Initialize with Token model."""
        super().__init__(Token)

    # Synchronous methods
    def get_by_location(
        self,
        session: Session,
        sura: int,
        aya: int,
        position: int,
    ) -> Optional[Token]:
        """Get token by exact location."""
        stmt = select(Token).where(
            Token.sura == sura,
            Token.aya == aya,
            Token.position == position,
        )
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    def get_verse_tokens(
        self,
        session: Session,
        sura: int,
        aya: int,
    ) -> list[Token]:
        """Get all tokens for a specific verse."""
        stmt = (
            select(Token)
            .where(Token.sura == sura, Token.aya == aya)
            .order_by(Token.position)
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    def get_by_root(
        self,
        session: Session,
        root: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """Get all tokens with a specific root."""
        stmt = (
            select(Token)
            .where(Token.root == root)
            .order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    def search(
        self,
        session: Session,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """Search tokens by Arabic text or normalized form."""
        search_pattern = f"%{query}%"
        stmt = (
            select(Token)
            .where(
                or_(
                    Token.text_ar.like(search_pattern),
                    Token.normalized.like(search_pattern),
                )
            )
            .order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    def count_by_sura(self, session: Session, sura: int) -> int:
        """Count tokens in a specific sura."""
        stmt = select(func.count()).select_from(Token).where(Token.sura == sura)
        result = session.execute(stmt)
        return result.scalar() or 0

    def count_by_root(self, session: Session, root: str) -> int:
        """Count tokens with a specific root."""
        stmt = select(func.count()).select_from(Token).where(Token.root == root)
        result = session.execute(stmt)
        return result.scalar() or 0

    def get_tokens_missing_roots(
        self,
        session: Session,
        limit: int = 100,
    ) -> list[Token]:
        """Get tokens that don't have roots yet."""
        stmt = (
            select(Token)
            .where(Token.status == TokenStatus.MISSING.value)
            .limit(limit)
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    def get_tokens_missing_roots_by_sura(
        self,
        session: Session,
        sura: int,
        limit: int = 10000,
    ) -> list[Token]:
        """Get tokens that don't have roots yet for a specific sura."""
        stmt = (
            select(Token)
            .where(
                Token.sura == sura,
                Token.status == TokenStatus.MISSING.value,
            )
            .order_by(Token.aya, Token.position)
            .limit(limit)
        )
        result = session.execute(stmt)
        return list(result.scalars().all())

    def get_filtered(
        self,
        session: Session,
        sura: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """Get tokens with filters (synchronous)."""
        stmt = select(Token)
        
        if sura is not None:
            stmt = stmt.where(Token.sura == sura)
        
        stmt = (
            stmt.order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )
        
        result = session.execute(stmt)
        return list(result.scalars().all())

    # Async methods
    async def aget_by_location(
        self,
        session: AsyncSession,
        sura: int,
        aya: int,
        position: int,
    ) -> Optional[Token]:
        """Get token by exact location (async)."""
        stmt = select(Token).where(
            Token.sura == sura,
            Token.aya == aya,
            Token.position == position,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def aget_verse_tokens(
        self,
        session: AsyncSession,
        sura: int,
        aya: int,
    ) -> list[Token]:
        """Get all tokens for a specific verse (async), eager-loading root_rel."""
        stmt = (
            select(Token)
            .where(Token.sura == sura, Token.aya == aya)
            .options(selectinload(Token.root_rel))
            .order_by(Token.position)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def aget_by_root(
        self,
        session: AsyncSession,
        root: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """Get all tokens with a specific root (async), eager-loading verse."""
        stmt = (
            select(Token)
            .where(Token.root == root)
            .options(selectinload(Token.verse))
            .order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def asearch(
        self,
        session: AsyncSession,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """Search tokens by Arabic text or normalized form (async)."""
        search_pattern = f"%{query}%"
        stmt = (
            select(Token)
            .where(
                or_(
                    Token.text_ar.like(search_pattern),
                    Token.normalized.like(search_pattern),
                )
            )
            .order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def aget_filtered(
        self,
        session: AsyncSession,
        sura: Optional[int] = None,
        root: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """Get tokens with multiple filters (async)."""
        stmt = select(Token)

        # Apply filters
        if sura is not None:
            stmt = stmt.where(Token.sura == sura)
        if root is not None:
            stmt = stmt.where(Token.root == root)
        if search is not None:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Token.text_ar.like(search_pattern),
                    Token.normalized.like(search_pattern),
                )
            )

        # Apply ordering and pagination
        stmt = (
            stmt.order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def acount_filtered(
        self,
        session: AsyncSession,
        sura: Optional[int] = None,
        root: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count tokens with filters (async)."""
        stmt = select(func.count()).select_from(Token)

        if sura is not None:
            stmt = stmt.where(Token.sura == sura)
        if root is not None:
            stmt = stmt.where(Token.root == root)
        if search is not None:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Token.text_ar.like(search_pattern),
                    Token.normalized.like(search_pattern),
                )
            )

        result = await session.execute(stmt)
        return result.scalar() or 0

    # ── Verse-aware queries ────────────────────────────────────────

    async def aget_verse(
        self,
        session: AsyncSession,
        sura: int,
        aya: int,
    ) -> Optional[Verse]:
        """Get a Verse row by sura/aya, eager-loading its tokens."""
        stmt = (
            select(Verse)
            .where(Verse.sura == sura, Verse.aya == aya)
            .options(selectinload(Verse.tokens))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
