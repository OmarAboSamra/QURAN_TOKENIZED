"""
Core Qur'an data API routes with advanced filters and caching.

This is the main API router, providing eight endpoints:

    GET   /quran/token/{id}        – Retrieve a single word token by ID
    GET   /quran/tokens            – Paginated list with sura/root/search filters
    GET   /quran/verse/{sura}/{aya} – Complete verse reconstructed from tokens
    GET   /quran/root/{root}       – All tokens sharing a given Arabic root
    GET   /quran/search?q=...      – Full-text search in Arabic text
    GET   /quran/stats             – Aggregate statistics (total tokens/verses/roots)
    PATCH /quran/token/{id}        – Update a token's root / status / interpretations
    PATCH /quran/root/{root}       – Update a root's meaning / metadata

Each endpoint:
    1. Checks the Redis cache (if enabled)
    2. Queries the database via TokenRepository
    3. Logs the request and records Prometheus metrics
    4. Returns a Pydantic response model

PATCH endpoints require the X-API-Key header when ADMIN_API_KEY is set.
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    RootResponse,
    RootTokensResponse,
    RootUpdateRequest,
    StatsResponse,
    TokenListResponse,
    TokenResponse,
    TokenUpdateRequest,
    VerseResponse,
)
from backend.cache import get_cache
from backend.config import get_settings
from backend.db import get_db_session
from backend.logging_config import get_logger, log_cache_operation, log_request
from backend.metrics import record_cache_operation, record_token_operation
from backend.models import Token
from backend.repositories.token_repository import TokenRepository

router = APIRouter(prefix="/quran", tags=["Quran"])
logger = get_logger(__name__)
cache = get_cache()
token_repo = TokenRepository()
settings = get_settings()


# ── Auth dependency ───────────────────────────────────────────────

async def require_admin(x_api_key: Optional[str] = Header(None)) -> None:
    """
    Validate the X-API-Key header for write endpoints.

    When ADMIN_API_KEY is empty (default), auth is disabled — any caller
    can use the PATCH endpoints. Set the env var to lock them down.
    """
    key = settings.admin_api_key
    if key and x_api_key != key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-API-Key header",
        )


# Endpoints
@router.get(
    "/token/{token_id}",
    response_model=TokenResponse,
    summary="Get single token",
    description="Retrieve a specific token by its ID",
)
async def get_token(
    token_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Get a single token by ID."""
    start_time = time.time()

    token = await token_repo.aget_by_id(db, token_id)

    if not token:
        record_token_operation("get_token", "not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token with ID {token_id} not found",
        )

    duration_ms = (time.time() - start_time) * 1000
    log_request(logger, "GET", f"/quran/token/{token_id}", 200, duration_ms)
    record_token_operation("get_token", "success")

    return TokenResponse.model_validate(token)


@router.get(
    "/tokens",
    response_model=TokenListResponse,
    summary="List tokens with filters",
    description="Get paginated list of tokens with optional filters for sura, root, and search",
)
async def get_tokens(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sura: Optional[int] = Query(None, ge=1, le=114, description="Filter by sura number"),
    root: Optional[str] = Query(None, min_length=1, max_length=50, description="Filter by Arabic root"),
    search: Optional[str] = Query(None, min_length=1, description="Search in Arabic text"),
    db: AsyncSession = Depends(get_db_session),
) -> TokenListResponse:
    """
    Get a paginated list of tokens with advanced filtering.

    Filters:
    - sura: Filter by surah number (1-114)
    - root: Filter by Arabic root
    - search: Search in Arabic text (text_ar or normalized)
    """
    start_time = time.time()
    skip = (page - 1) * page_size

    # Get filtered tokens
    tokens = await token_repo.aget_filtered(
        db,
        sura=sura,
        root=root,
        search=search,
        skip=skip,
        limit=page_size,
    )

    # Get total count with same filters
    total = await token_repo.acount_filtered(
        db,
        sura=sura,
        root=root,
        search=search,
    )

    duration_ms = (time.time() - start_time) * 1000
    log_request(
        logger,
        "GET",
        "/quran/tokens",
        200,
        duration_ms,
        filters={"sura": sura, "root": root, "search": search},
        results=len(tokens),
    )
    record_token_operation("list_tokens", "success")

    return TokenListResponse(
        tokens=[TokenResponse.model_validate(t) for t in tokens],
        total=total,
        page=page,
        page_size=page_size,
        filters={"sura": sura, "root": root, "search": search},
    )


@router.get(
    "/verse/{sura}/{aya}",
    response_model=VerseResponse,
    summary="Get complete verse",
    description="Retrieve a complete verse (ayah) with all its word tokens",
)
async def get_verse(
    sura: int = Path(..., ge=1, le=114, description="Surah number"),
    aya: int = Path(..., ge=1, description="Ayah number"),
    db: AsyncSession = Depends(get_db_session),
) -> VerseResponse:
    """Get a complete verse with all its tokens."""
    start_time = time.time()

    # Try cache first
    cached = await cache.get_verse(sura, aya)
    if cached:
        log_cache_operation(logger, "get", f"verse:{sura}:{aya}", hit=True)
        record_cache_operation("get", "hit")
        return VerseResponse(**cached)

    record_cache_operation("get", "miss")

    # Try the Verse table first (populated by migration or tokenize_quran.py).
    # This loads the verse + its tokens in a single query via selectinload.
    verse_obj = await token_repo.aget_verse(db, sura, aya)

    if verse_obj and verse_obj.tokens:
        tokens = verse_obj.tokens
        text_ar = verse_obj.text_ar
    else:
        # Fallback: reconstruct from Token table (no Verse row yet)
        tokens = await token_repo.aget_verse_tokens(db, sura, aya)
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verse {sura}:{aya} not found",
            )
        text_ar = " ".join(t.text_ar for t in tokens)

    token_dicts = [TokenResponse.model_validate(t).model_dump() for t in tokens]

    response_data = {
        "sura": sura,
        "aya": aya,
        "tokens": token_dicts,
        "text_ar": text_ar,
        "word_count": len(tokens),
    }

    # Cache the response
    await cache.set_verse(sura, aya, response_data)

    duration_ms = (time.time() - start_time) * 1000
    log_request(logger, "GET", f"/quran/verse/{sura}/{aya}", 200, duration_ms)

    return VerseResponse(**response_data)


@router.get(
    "/root/{root}",
    response_model=RootTokensResponse,
    summary="Get tokens by root",
    description="Retrieve all word tokens that share the same Arabic root",
)
async def get_tokens_by_root(
    root: str = Path(..., min_length=1, max_length=50, description="Arabic root"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> RootTokensResponse:
    """
    Get all tokens that share the same Arabic root.

    This endpoint is useful for finding all occurrences of words
    derived from the same root throughout the Qur'an.
    """
    start_time = time.time()

    # Try cache first
    cached = await cache.get_tokens_by_root(root, page)
    if cached:
        log_cache_operation(logger, "get", f"tokens_root:{root}:{page}", hit=True)
        record_cache_operation("get", "hit")
        return RootTokensResponse(**cached)

    record_cache_operation("get", "miss")

    # Fetch from database
    skip = (page - 1) * page_size
    tokens = await token_repo.aget_by_root(db, root, skip, page_size)
    total_count = await token_repo.acount_filtered(db, root=root)

    token_dicts = [TokenResponse.model_validate(t).model_dump() for t in tokens]

    response_data = {
        "root": root,
        "total_count": total_count,
        "tokens": token_dicts,
        "page": page,
        "page_size": page_size,
    }

    # Cache the response
    await cache.set_tokens_by_root(root, page, response_data)

    duration_ms = (time.time() - start_time) * 1000
    log_request(
        logger,
        "GET",
        f"/quran/root/{root}",
        200,
        duration_ms,
        results=len(tokens),
    )
    record_token_operation("get_by_root", "success")

    return RootTokensResponse(**response_data)


@router.get(
    "/search",
    response_model=TokenListResponse,
    summary="Search tokens",
    description="Search for tokens by Arabic text (with or without diacritics)",
)
async def search_tokens(
    q: str = Query(..., min_length=1, description="Search query (Arabic text)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> TokenListResponse:
    """Search for tokens containing the specified Arabic text.

    Uses the FTS5 full-text index when available for fast ranked search,
    with automatic fallback to LIKE for databases without FTS5.
    """
    start_time = time.time()
    skip = (page - 1) * page_size

    tokens = await token_repo.asearch_fts(db, q, skip, page_size)
    total = await token_repo.acount_fts(db, q)

    duration_ms = (time.time() - start_time) * 1000
    log_request(
        logger,
        "GET",
        "/quran/search",
        200,
        duration_ms,
        query=q,
        results=len(tokens),
    )

    return TokenListResponse(
        tokens=[TokenResponse.model_validate(t) for t in tokens],
        total=total,
        page=page,
        page_size=page_size,
        filters={"search": q},
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get statistics",
    description="Get overall statistics about the tokenized Qur'an data",
)
async def get_stats(
    sura: Optional[int] = Query(None, ge=1, le=114, description="Optional: Get stats for specific sura"),
    db: AsyncSession = Depends(get_db_session),
) -> StatsResponse:
    """Get overall statistics about the dataset or for a specific sura."""
    start_time = time.time()

    from sqlalchemy import func, select

    from backend.models import Verse

    if sura:
        # Sura-specific stats
        total_tokens = await token_repo.acount_filtered(db, sura=sura)
        
        # Count verses from the Verse table (preferred) or fall back to Token
        verse_count_q = select(func.count()).select_from(Verse).where(Verse.sura == sura)
        verse_result = await db.execute(verse_count_q)
        total_verses = verse_result.scalar() or 0

        if total_verses == 0:
            # Fallback: count distinct (sura, aya) from tokens
            verse_subq = select(Token.sura, Token.aya).where(Token.sura == sura).distinct().subquery()
            verse_result = await db.execute(select(func.count()).select_from(verse_subq))
            total_verses = verse_result.scalar() or 0
        
        # Count distinct roots in this sura
        root_count_query = select(func.count(func.distinct(Token.root))).where(
            Token.sura == sura,
            Token.root.isnot(None)
        )
        root_result = await db.execute(root_count_query)
        total_roots = root_result.scalar() or 0
    else:
        # Overall stats
        total_tokens = await token_repo.acount(db)

        # Count verses from Verse table (preferred) or fall back to Token
        verse_count_q = select(func.count()).select_from(Verse)
        verse_result = await db.execute(verse_count_q)
        total_verses = verse_result.scalar() or 0

        if total_verses == 0:
            verse_subq = select(Token.sura, Token.aya).distinct().subquery()
            verse_result = await db.execute(select(func.count()).select_from(verse_subq))
            total_verses = verse_result.scalar() or 0

        # Count distinct roots
        root_count_query = select(func.count(func.distinct(Token.root))).where(
            Token.root.isnot(None)
        )
        root_result = await db.execute(root_count_query)
        total_roots = root_result.scalar() or 0

    duration_ms = (time.time() - start_time) * 1000
    log_request(logger, "GET", "/quran/stats", 200, duration_ms, sura=sura)

    return StatsResponse(
        total_tokens=total_tokens,
        total_verses=total_verses,
        total_roots=total_roots,
        suras=114,
    )


# ── PATCH endpoints (D5: manual corrections) ─────────────────────


@router.patch(
    "/token/{token_id}",
    response_model=TokenResponse,
    summary="Update token",
    description="Correct a token's root, status, or interpretations. Requires X-API-Key when ADMIN_API_KEY is set.",
    dependencies=[Depends(require_admin)],
)
async def update_token(
    token_id: int,
    body: TokenUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Update a token's root, status, and/or interpretations.

    If the root is changed the token's root_id FK is re-linked to the
    correct Root row (created on the fly if needed), and the old/new
    Root.token_count counters are adjusted. Related cache keys are
    invalidated.
    """
    start_time = time.time()

    token = await token_repo.aget_by_id(db, token_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_id} not found",
        )

    old_root = token.root

    # Apply root change (with FK re-link)
    if body.root is not None and body.root != token.root:
        token = await token_repo.aupdate_token_root(db, token, body.root)

    # Apply other fields
    updates: dict = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.interpretations is not None:
        updates["interpretations"] = body.interpretations
    if updates:
        token = await token_repo.aupdate(db, token, **updates)

    await db.commit()

    # Invalidate cache for the affected verse and root(s)
    await cache.invalidate_verse(token.sura, token.aya)
    if old_root:
        await cache.delete_pattern(f"tokens_root:{old_root}:*")
    if body.root and body.root != old_root:
        await cache.delete_pattern(f"tokens_root:{body.root}:*")

    duration_ms = (time.time() - start_time) * 1000
    log_request(logger, "PATCH", f"/quran/token/{token_id}", 200, duration_ms)
    record_token_operation("update_token", "success")

    return TokenResponse.model_validate(token)


@router.patch(
    "/root/{root}",
    response_model=RootResponse,
    summary="Update root",
    description="Update a root's meaning or metadata. Requires X-API-Key when ADMIN_API_KEY is set.",
    dependencies=[Depends(require_admin)],
)
async def update_root(
    root: str = Path(..., min_length=1, max_length=50, description="Arabic root"),
    body: RootUpdateRequest = ...,
    db: AsyncSession = Depends(get_db_session),
) -> RootResponse:
    """
    Update a root's meaning and/or metadata.

    The root row must already exist (created during root extraction or
    when a token's root is corrected via PATCH /quran/token/{id}).
    """
    start_time = time.time()

    root_obj = await token_repo.aget_root_by_name(db, root)
    if not root_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Root '{root}' not found",
        )

    updates: dict = {}
    if body.meaning is not None:
        updates["meaning"] = body.meaning
    if body.metadata_ is not None:
        updates["metadata_"] = body.metadata_

    if updates:
        for key, value in updates.items():
            setattr(root_obj, key, value)
        await db.flush()

    await db.commit()

    # Invalidate cached token lists for this root
    await cache.delete_pattern(f"tokens_root:{root}:*")

    duration_ms = (time.time() - start_time) * 1000
    log_request(logger, "PATCH", f"/quran/root/{root}", 200, duration_ms)

    return RootResponse(
        id=root_obj.id,
        root=root_obj.root,
        meaning=root_obj.meaning,
        token_count=root_obj.token_count,
        metadata=root_obj.metadata_,
    )
