"""
ORM model for Arabic roots.

The Root table provides a reverse index: given a root string like "كتب",
quickly find how many tokens share it and what it means.

Design note:
    token_ids is a legacy JSON column that stores a flat list of Token IDs.
    For roots with thousands of occurrences this doesn't scale well.
    A proper many-to-many relationship (via Token.root FK) is preferred
    for production queries — the API already queries Token directly.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base
from backend.models.types import JSONType


class Root(Base):
    """
    An Arabic root with aggregated metadata.
    
    Each root (e.g. كتب, قرأ) appears once in this table. The
    token_count field caches how many tokens share this root for
    fast statistics without counting the Token table.
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
        JSONType,
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
        JSONType,
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
