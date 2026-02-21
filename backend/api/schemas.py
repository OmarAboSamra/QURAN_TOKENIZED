"""
Shared Pydantic response models for the Qur'an API.

These models define the JSON shape returned by all /quran/* endpoints.
They use `from_attributes = True` (Pydantic v2) to allow direct
validation from SQLAlchemy ORM instances via model_validate().
"""
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class TokenResponse(BaseModel):
    """Response model for a single token."""

    id: int
    sura: int
    aya: int
    position: int
    text_ar: str
    normalized: str
    root: Optional[str] = None
    root_id: Optional[int] = None
    verse_id: Optional[int] = None
    pattern: Optional[str] = None
    status: str
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

    @computed_field
    @property
    def total_pages(self) -> int:
        """Number of pages based on total and page_size."""
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0


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


# ── Request models for PATCH endpoints (D5) ──────────────────────


class TokenUpdateRequest(BaseModel):
    """Request body for PATCH /quran/token/{id}."""

    root: Optional[str] = Field(None, max_length=50, description="Corrected Arabic root")
    status: Optional[str] = Field(None, description="New status (verified, manual_review, …)")
    interpretations: Optional[dict] = Field(None, description="Meanings / translations / notes")


class RootUpdateRequest(BaseModel):
    """Request body for PATCH /quran/root/{root}."""

    meaning: Optional[str] = Field(None, description="English meaning or definition")
    metadata_: Optional[dict] = Field(None, alias="metadata", description="Additional metadata (etymology, related roots, …)")
    related_roots: Optional[list[str]] = Field(None, description="List of similar/related root strings")

    class Config:
        """Pydantic config."""

        populate_by_name = True


class RootResponse(BaseModel):
    """Response model for a single root."""

    id: int
    root: str
    meaning: Optional[str] = None
    token_count: int = 0
    metadata: Optional[dict] = Field(None)
    related_roots: Optional[list[str]] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class SimilarWordEntry(BaseModel):
    """A single similar-word result with distance info."""

    normalized: str
    distance: int
    root: Optional[str] = None
    sample_text_ar: Optional[str] = None
    count: int = 0


class SimilarWordsResponse(BaseModel):
    """Response model for GET /quran/similar/{word}."""

    query: str
    max_distance: int
    results: list[SimilarWordEntry]
    total: int
