"""
ORM model for Qur'an word tokens.

The Token table is the central table of the system. Each row represents one
word in the Qur'an, uniquely located by (sura, aya, position). The primary
workflow is:

    1. Tokenize  – split raw text into words, store text_ar + normalized
    2. Extract   – query multiple Arabic root dictionaries, store root_sources
    3. Verify    – compare sources, set consensus root + status
    4. Link      – set root_id FK to associate token with its Root row
    5. Annotate  – (future) add interpretations, translations, context notes

Relationships:
    Token.root_rel  → Root  (many-to-one via root_id FK)
    Token.verse     → Verse (many-to-one via verse_id FK)

Status lifecycle:
    MISSING → VERIFIED         (sources agree)
    MISSING → DISCREPANCY      (sources disagree but majority exists)
    MISSING → MANUAL_REVIEW    (low confidence or no majority)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base
from backend.models.types import JSONType

if TYPE_CHECKING:
    from backend.models.root_model import Root
    from backend.models.verse_model import Verse


class TokenStatus(str, Enum):
    """Status of root extraction for a token."""

    MISSING = "missing"  # Root not yet extracted
    VERIFIED = "verified"  # Root verified from multiple sources
    DISCREPANCY = "discrepancy"  # Conflicting roots from different sources
    MANUAL_REVIEW = "manual_review"  # Flagged for manual review


class Token(Base):
    """
    A single word token extracted from the Qur'an.
    
    Uniquely identified by (sura, aya, position). Contains the original
    Arabic text with diacritics, a normalized form for comparison, and
    root extraction results from multiple sources.
    
    Key fields for the analysis use case:
      - root:            the consensus Arabic root string (e.g. كتب)
      - root_id:         FK to the Root table for relational queries
      - verse_id:        FK to the Verse table for verse-level access
      - root_sources:    JSON {"qurancorpus": "كتب", "almaany": "كتب", ...}
      - interpretations: (future) meanings, translations, usage notes
    """

    __tablename__ = "tokens"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Location identifiers
    sura: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    aya: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Word position within the verse (0-indexed)",
    )

    # Text content
    text_ar: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original Arabic word with diacritics",
    )
    normalized: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
        comment="Normalized Arabic text without diacritics",
    )

    # Root information
    root: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Verified Arabic root (denormalized for fast filtering)",
    )
    root_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("roots.id", name="fk_tokens_root_id"),
        nullable=True,
        index=True,
        comment="FK to roots table for relational queries",
    )
    root_sources: Mapped[Optional[dict]] = mapped_column(
        JSONType,
        nullable=True,
        comment="JSON object mapping source name to extracted root",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TokenStatus.MISSING.value,
        index=True,
        comment="Current status of root extraction",
    )

    # Verse FK — links this token to its parent verse
    verse_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("verses.id", name="fk_tokens_verse_id"),
        nullable=True,
        index=True,
        comment="FK to verses table",
    )

    # DEPRECATED: Use root_id relationship instead.
    # Kept for backward compatibility; not populated by new code.
    references: Mapped[Optional[list]] = mapped_column(
        JSONType,
        nullable=True,
        comment="DEPRECATED – list of token IDs sharing the same root",
    )

    # Future: meaning and translation fields
    interpretations: Mapped[Optional[dict]] = mapped_column(
        JSONType,
        nullable=True,
        comment="JSON object with meanings, translations, context",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("ix_tokens_sura_aya", "sura", "aya"),
        Index("ix_tokens_sura_aya_position", "sura", "aya", "position", unique=True),
        Index("ix_tokens_root_status", "root", "status"),
        Index("ix_tokens_root_id", "root_id"),
        Index("ix_tokens_verse_id", "verse_id"),
    )

    # ── ORM Relationships ──────────────────────────────────────────
    # Use these for JOINs and eager loading instead of manual queries.

    root_rel: Mapped[Optional["Root"]] = relationship(
        "Root",
        back_populates="tokens",
        lazy="select",
    )
    """The Root object this token belongs to (via root_id FK)."""

    verse: Mapped[Optional["Verse"]] = relationship(
        "Verse",
        back_populates="tokens",
        lazy="select",
    )
    """The Verse object this token belongs to (via verse_id FK)."""

    def __repr__(self) -> str:
        """String representation of token."""
        return (
            f"<Token(id={self.id}, "
            f"sura={self.sura}, "
            f"aya={self.aya}, "
            f"pos={self.position}, "
            f"text='{self.text_ar}', "
            f"root='{self.root}')>"
        )
