"""ORM models for Qur'an tokens (words, verses, etc.)."""
import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, TypeDecorator, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base
from backend.config import get_settings

_settings = get_settings()
_is_postgres = _settings.database_url.startswith(("postgresql://", "postgresql+"))


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL JSONB and SQLite Text."""
    
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value


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
    Represents a single word token from the Qur'an.
    
    Each token is uniquely identified by its position in the text
    (sura, aya, position within aya).
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
