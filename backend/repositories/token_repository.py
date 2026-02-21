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

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from backend.models.root_model import Root
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

    # ── Root-aware queries ─────────────────────────────────────────

    async def aget_root_by_name(
        self,
        session: AsyncSession,
        root_str: str,
    ) -> Optional[Root]:
        """Get a Root row by its root string."""
        stmt = select(Root).where(Root.root == root_str)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def aupdate_token_root(
        self,
        session: AsyncSession,
        token: Token,
        new_root: str,
    ) -> Token:
        """
        Update a token's root and re-link its root_id FK.

        If the Root row for *new_root* doesn't exist it is created.
        Token counts on old and new Root rows are adjusted.
        """
        old_root_str = token.root

        # Find or create the new Root row
        new_root_obj = await self.aget_root_by_name(session, new_root)
        if not new_root_obj:
            new_root_obj = Root(root=new_root, token_count=0, token_ids=[])
            session.add(new_root_obj)
            await session.flush()

        token.root = new_root
        token.root_id = new_root_obj.id
        new_root_obj.token_count = (new_root_obj.token_count or 0) + 1

        # Decrement old root's counter
        if old_root_str:
            old_root_obj = await self.aget_root_by_name(session, old_root_str)
            if old_root_obj and old_root_obj.token_count and old_root_obj.token_count > 0:
                old_root_obj.token_count -= 1

        await session.flush()
        return token

    # ── FTS5 search ────────────────────────────────────────────────

    async def asearch_fts(
        self,
        session: AsyncSession,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Token]:
        """
        Search tokens using FTS5 full-text index (fast).

        Falls back to LIKE if the FTS5 table doesn't exist.
        """
        try:
            # FTS5 match query — returns rowids matching the query
            fts_stmt = text(
                "SELECT rowid FROM tokens_fts WHERE tokens_fts MATCH :q "
                "ORDER BY rank LIMIT :lim OFFSET :off"
            )
            result = await session.execute(
                fts_stmt, {"q": query, "lim": limit, "off": skip}
            )
            rowids = [row[0] for row in result.fetchall()]
            if not rowids:
                return []
            # Fetch full Token rows by the matched IDs
            stmt = (
                select(Token)
                .where(Token.id.in_(rowids))
                .order_by(Token.sura, Token.aya, Token.position)
            )
            token_result = await session.execute(stmt)
            return list(token_result.scalars().all())
        except Exception:
            # FTS5 table missing or query syntax error → fall back to LIKE
            return await self.asearch(session, query, skip, limit)

    async def acount_fts(
        self,
        session: AsyncSession,
        query: str,
    ) -> int:
        """Count FTS5 matches, falling back to LIKE count."""
        try:
            fts_count = text(
                "SELECT count(*) FROM tokens_fts WHERE tokens_fts MATCH :q"
            )
            result = await session.execute(fts_count, {"q": query})
            return result.scalar() or 0
        except Exception:
            return await self.acount_filtered(session, search=query)

    # ── Similar-word queries (D7) ──────────────────────────────────

    async def aget_similar_by_normalized(
        self,
        session: AsyncSession,
        normalized: str,
        limit: int = 50,
    ) -> list[Token]:
        """
        Get tokens whose normalized form matches exactly.

        This is the fast path — used to collect all surface forms of the
        same underlying word (e.g. "الله" with various diacritics).
        """
        stmt = (
            select(Token)
            .where(Token.normalized == normalized)
            .order_by(Token.sura, Token.aya, Token.position)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def aget_by_pattern(
        self,
        session: AsyncSession,
        pattern: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Token]:
        """Get tokens that share the same morphological pattern (وزن)."""
        stmt = (
            select(Token)
            .where(Token.pattern == pattern)
            .order_by(Token.sura, Token.aya, Token.position)
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def aget_distinct_normalized_forms(
        self,
        session: AsyncSession,
        limit: int = 5000,
    ) -> list[str]:
        """
        Return a sample of distinct normalized word forms.

        Used by the Levenshtein similarity search to build a candidate
        set without loading full Token rows.
        """
        stmt = (
            select(func.distinct(Token.normalized))
            .order_by(Token.normalized)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def aget_root_with_related(
        self,
        session: AsyncSession,
        root_str: str,
    ) -> tuple[Optional[Root], list[Root]]:
        """
        Get a Root and its related roots.

        Returns (root_obj, list_of_related_Root_objects).
        """
        root_obj = await self.aget_root_by_name(session, root_str)
        if not root_obj:
            return None, []

        related: list[Root] = []
        if root_obj.related_roots:
            for rr in root_obj.related_roots:
                rr_obj = await self.aget_root_by_name(session, rr)
                if rr_obj:
                    related.append(rr_obj)

        return root_obj, related
