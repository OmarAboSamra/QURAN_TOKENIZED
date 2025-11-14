"""Qur'an data API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db_session
from backend.models import Root, Token

router = APIRouter(prefix="/quran", tags=["Quran"])


# Response Models
class TokenResponse(BaseModel):
    """Response model for a single token."""

    id: int
    sura: int
    aya: int
    position: int
    text_ar: str
    normalized: str
    root: Optional[str] = None
    status: str
    references: Optional[list[int]] = None
    interpretations: Optional[dict] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class TokenListResponse(BaseModel):
    """Response model for a list of tokens."""

    tokens: list[TokenResponse]
    total: int
    page: int
    page_size: int


class RootResponse(BaseModel):
    """Response model for a root."""

    id: int
    root: str
    meaning: Optional[str] = None
    token_count: int
    tokens: list[int]

    class Config:
        """Pydantic config."""

        from_attributes = True


class VerseResponse(BaseModel):
    """Response model for a complete verse."""

    sura: int
    aya: int
    tokens: list[TokenResponse]
    text_ar: str
    word_count: int


class StatsResponse(BaseModel):
    """Response model for statistics."""

    total_tokens: int
    total_roots: int
    verified_roots: int
    pending_review: int
    total_suras: int
    total_verses: int


# Endpoints
@router.get(
    "/token/{token_id}",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def get_token(
    token_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Get a single token by ID.
    
    Args:
        token_id: Token ID
        db: Database session
        
    Returns:
        Token data
    """
    result = await db.execute(select(Token).where(Token.id == token_id))
    token = result.scalar_one_or_none()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token with ID {token_id} not found",
        )
    
    return TokenResponse.model_validate(token)


@router.get(
    "/tokens",
    response_model=TokenListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tokens(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sura: Optional[int] = Query(None, ge=1, le=114, description="Filter by sura"),
    aya: Optional[int] = Query(None, ge=1, description="Filter by aya"),
    root: Optional[str] = Query(None, description="Filter by root"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db_session),
) -> TokenListResponse:
    """
    Get a paginated list of tokens with optional filters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        sura: Optional sura filter
        aya: Optional aya filter
        root: Optional root filter
        status_filter: Optional status filter
        db: Database session
        
    Returns:
        Paginated list of tokens
    """
    # Build query
    query = select(Token)
    
    if sura:
        query = query.where(Token.sura == sura)
    if aya:
        query = query.where(Token.aya == aya)
    if root:
        query = query.where(Token.root == root)
    if status_filter:
        query = query.where(Token.status == status_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    tokens = result.scalars().all()
    
    return TokenListResponse(
        tokens=[TokenResponse.model_validate(t) for t in tokens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/verse/{sura}/{aya}",
    response_model=VerseResponse,
    status_code=status.HTTP_200_OK,
)
async def get_verse(
    sura: int,
    aya: int,
    db: AsyncSession = Depends(get_db_session),
) -> VerseResponse:
    """
    Get a complete verse with all its tokens.
    
    Args:
        sura: Sura number (1-114)
        aya: Aya number
        db: Database session
        
    Returns:
        Complete verse data
    """
    query = (
        select(Token)
        .where(Token.sura == sura, Token.aya == aya)
        .order_by(Token.position)
    )
    
    result = await db.execute(query)
    tokens = result.scalars().all()
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verse {sura}:{aya} not found",
        )
    
    # Reconstruct Arabic text
    text_ar = " ".join(token.text_ar for token in tokens)
    
    return VerseResponse(
        sura=sura,
        aya=aya,
        tokens=[TokenResponse.model_validate(t) for t in tokens],
        text_ar=text_ar,
        word_count=len(tokens),
    )


@router.get(
    "/root/{root}",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
)
async def get_root(
    root: str,
    db: AsyncSession = Depends(get_db_session),
) -> RootResponse:
    """
    Get all tokens sharing a specific root.
    
    Args:
        root: Arabic root text
        db: Database session
        
    Returns:
        Root data with all related tokens
    """
    result = await db.execute(select(Root).where(Root.root == root))
    root_obj = result.scalar_one_or_none()
    
    if not root_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Root '{root}' not found",
        )
    
    return RootResponse.model_validate(root_obj)


@router.get(
    "/search",
    response_model=TokenListResponse,
    status_code=status.HTTP_200_OK,
)
async def search_tokens(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
) -> TokenListResponse:
    """
    Search tokens by Arabic text or normalized form.
    
    Args:
        q: Search query
        page: Page number
        page_size: Items per page
        db: Database session
        
    Returns:
        Matching tokens
    """
    # Search in both text_ar and normalized fields
    query = select(Token).where(
        (Token.text_ar.contains(q)) | (Token.normalized.contains(q))
    )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    tokens = result.scalars().all()
    
    return TokenListResponse(
        tokens=[TokenResponse.model_validate(t) for t in tokens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_statistics(
    db: AsyncSession = Depends(get_db_session),
) -> StatsResponse:
    """
    Get overall statistics about the Qur'an database.
    
    Args:
        db: Database session
        
    Returns:
        Statistics
    """
    # Total tokens
    total_tokens_result = await db.execute(select(func.count(Token.id)))
    total_tokens = total_tokens_result.scalar_one()
    
    # Total roots
    total_roots_result = await db.execute(select(func.count(Root.id)))
    total_roots = total_roots_result.scalar_one()
    
    # Verified roots
    verified_result = await db.execute(
        select(func.count(Token.id)).where(Token.status == "verified")
    )
    verified_roots = verified_result.scalar_one()
    
    # Pending review
    pending_result = await db.execute(
        select(func.count(Token.id)).where(
            Token.status.in_(["discrepancy", "manual_review"])
        )
    )
    pending_review = pending_result.scalar_one()
    
    # Unique suras
    unique_suras_result = await db.execute(select(func.count(func.distinct(Token.sura))))
    total_suras = unique_suras_result.scalar_one()
    
    # Unique verses - count distinct sura||aya combinations
    verse_subq = select(Token.sura, Token.aya).distinct().subquery()
    unique_verses_result = await db.execute(select(func.count()).select_from(verse_subq))
    total_verses = unique_verses_result.scalar() or 0
    
    return StatsResponse(
        total_tokens=total_tokens,
        total_roots=total_roots,
        verified_roots=verified_roots,
        pending_review=pending_review,
        total_suras=total_suras,
        total_verses=total_verses,
    )
