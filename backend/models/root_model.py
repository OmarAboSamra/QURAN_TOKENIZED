"""ORM model for Arabic roots."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.token_model import Token


class Root(Base):
    """
    Represents an Arabic root with all tokens that share it.
    
    This table provides a reverse index for fast lookup of all words
    derived from the same root.
    """

    __tablename__ = "roots"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Root text
    root: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Arabic root text",
    )

    # Optional meaning
    meaning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="English meaning or definition of the root",
    )

    # Compressed list of token IDs (legacy - prefer using relationship)
    token_ids: Mapped[Optional[list]] = mapped_column(
        "tokens",  # Keep same column name for backward compatibility
        JSONB if True else Text,  # JSONB for PostgreSQL, Text for SQLite
        nullable=True,
        comment="List of token IDs that share this root (legacy field)",
    )

    # Statistics
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of tokens with this root",
    )

    # Additional metadata
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",  # Use different column name to avoid conflict with SQLAlchemy metadata
        JSONB if True else Text,  # JSONB for PostgreSQL, Text for SQLite
        nullable=True,
        comment="Additional metadata (etymology, related roots, etc.)",
    )

    # Timestamps
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

    # Indexes
    __table_args__ = (
        Index("ix_roots_token_count", "token_count"),
    )

    def __repr__(self) -> str:
        """String representation of root."""
        return (
            f"<Root(id={self.id}, "
            f"root='{self.root}', "
            f"tokens={self.token_count}, "
            f"meaning='{self.meaning[:30] if self.meaning else None}...')>"
        )
