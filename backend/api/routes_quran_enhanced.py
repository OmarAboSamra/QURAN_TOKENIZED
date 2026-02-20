"""Qur'an data API routes with advanced filters and caching."""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    RootTokensResponse,
    StatsResponse,
    TokenListResponse,
    TokenResponse,
    VerseResponse,
)
from backend.cache import get_cache
from backend.db import get_db_session
from backend.logging_config import get_logger, log_cache_operation, log_request
from backend.metrics import record_cache_operation, record_token_operation
from backend.models import Token
from backend.repositories.token_repository import TokenRepository

router = APIRouter(prefix="/quran", tags=["Quran"])
logger = get_logger(__name__)
cache = get_cache()
token_repo = TokenRepository()


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

    # Fetch from database
    tokens = await token_repo.aget_verse_tokens(db, sura, aya)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verse {sura}:{aya} not found",
        )

    # Reconstruct verse text
    text_ar = " ".join(t.text_ar for t in tokens)

    response_data = {
        "sura": sura,
        "aya": aya,
        "tokens": [TokenResponse.model_validate(t) for t in tokens],
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

    response_data = {
        "root": root,
        "total_count": total_count,
        "tokens": [TokenResponse.model_validate(t) for t in tokens],
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
    """Search for tokens containing the specified Arabic text."""
    start_time = time.time()
    skip = (page - 1) * page_size

    tokens = await token_repo.asearch(db, q, skip, page_size)
    total = await token_repo.acount_filtered(db, search=q)

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

    # Count distinct verses
    from sqlalchemy import func, select

    from backend.models import Token

    if sura:
        # Sura-specific stats
        total_tokens = await token_repo.acount_filtered(db, sura=sura)
        
        # Count distinct verses in this sura
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

        # Count distinct verses
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
