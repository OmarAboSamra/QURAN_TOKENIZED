"""
Shared Pydantic response models for the Qur'an API.

These models define the JSON shape returned by all /quran/* endpoints.
They use `from_attributes = True` (Pydantic v2) to allow direct
validation from SQLAlchemy ORM instances via model_validate().
"""
from typing import Optional

from pydantic import BaseModel, Field


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
    filters: dict = Field(default_factory=dict)


class VerseResponse(BaseModel):
    """Response model for a complete verse."""

    sura: int
    aya: int
    tokens: list[TokenResponse]
    text_ar: str
    word_count: int


class RootTokensResponse(BaseModel):
    """Response model for tokens sharing a root."""

    root: str
    total_count: int
    tokens: list[TokenResponse]
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """Response model for statistics."""

    total_tokens: int
    total_verses: int
    total_roots: int
    suras: int = 114
