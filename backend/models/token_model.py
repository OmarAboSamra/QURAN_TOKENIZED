"""
ORM model for Qur'an word tokens.

The Token table is the central table of the system. Each row represents one
word in the Qur'an, uniquely located by (sura, aya, position). The primary
workflow is:

    1. Tokenize  – split raw text into words, store text_ar + normalized
    2. Extract   – query multiple Arabic root dictionaries, store root_sources
    3. Verify    – compare sources, set consensus root + status
    4. Link      – build cross-references to other words sharing the same root
    5. Annotate  – (future) add interpretations, translations, context notes

Status lifecycle:
    MISSING → VERIFIED         (sources agree)
    MISSING → DISCREPANCY      (sources disagree but majority exists)
    MISSING → MANUAL_REVIEW    (low confidence or no majority)
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base
from backend.models.types import JSONType


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
      - root:          the consensus Arabic root (e.g. كتب)
      - root_sources:  JSON {"qurancorpus": "كتب", "almaany": "كتب", ...}
      - references:    list of other token IDs sharing the same root
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
        comment="Verified Arabic root",
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

    # References to other tokens with same root
    references: Mapped[Optional[list]] = mapped_column(
        JSONType,
        nullable=True,
        comment="List of token IDs sharing the same root",
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
    )

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
