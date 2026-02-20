"""ORM model for Qur'an verses."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base
from backend.models.types import JSONType


class Verse(Base):
    """
    Represents a single verse (ayah) from the Qur'an.
    
    Contains metadata about the verse and relationships to its constituent tokens.
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

    def __repr__(self) -> str:
        """String representation."""
        return f"<Verse(sura={self.sura}, aya={self.aya}, words={self.word_count})>"
