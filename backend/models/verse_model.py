"""
ORM model for Qur'an verses (ayat).

The Verse table stores complete verse text and metadata.

Relationships:
    Verse.tokens → list[Token]  (one-to-many via Token.verse_id FK)

The tokens relationship provides direct access to all words in a verse
without manual filtering by sura/aya. Verse rows are created during
tokenization (see scripts/tokenize_quran.py or the migration script).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base
from backend.models.types import JSONType

if TYPE_CHECKING:
    from backend.models.token_model import Token


class Verse(Base):
    """
    A single verse (ayah) from the Qur'an.
    
    Identified by (sura, aya) with a unique composite index.
    The metadata_ JSON field is reserved for future expansions
    like English translations, tafsir cross-references, etc.
    """

    __tablename__ = "verses"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Location identifiers
    sura: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Surah number (1-114)",
    )
    aya: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Ayah number within the surah",
    )

    # Text content
    text_ar: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Complete Arabic text of the verse",
    )
    text_normalized: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Normalized Arabic text without diacritics",
    )

    # Metadata
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of words in the verse",
    )
    
    # PostgreSQL JSONB field for additional metadata
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONType,
        nullable=True,
        comment="Additional verse metadata (translations, tafsir references, etc.)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Composite unique constraint
    __table_args__ = (
        Index("ix_verses_sura_aya", "sura", "aya", unique=True),
        Index("ix_verses_word_count", "word_count"),
    )

    # ── ORM Relationships ──────────────────────────────────────────
    tokens: Mapped[list["Token"]] = relationship(
        "Token",
        back_populates="verse",
        lazy="select",
        order_by="Token.position",
    )
    """All word tokens in this verse, ordered by position."""

    def __repr__(self) -> str:
        """String representation."""
        return f"<Verse(sura={self.sura}, aya={self.aya}, words={self.word_count})>"
