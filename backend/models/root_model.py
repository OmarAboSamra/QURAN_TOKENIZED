"""
ORM model for Arabic roots.

The Root table provides a reverse index: given a root string like "كتب",
quickly find all tokens that share it via the `tokens` relationship.

Relationships:
    Root.tokens → list[Token]  (one-to-many via Token.root_id FK)
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base
from backend.models.types import JSONType

if TYPE_CHECKING:
    from backend.models.token_model import Token


class Root(Base):
    """
    An Arabic root with aggregated metadata.
    
    Each root (e.g. كتب, قرأ) appears once in this table. Use the
    `tokens` relationship to get all Token rows sharing this root.
    The `token_count` field is a denormalized counter for fast stats.
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

    # DEPRECATED: Use the `tokens` relationship instead.
    # Kept for backward compatibility with old data; not populated by new code.
    token_ids: Mapped[Optional[list]] = mapped_column(
        "tokens_legacy",  # Renamed column to avoid clash with relationship name
        JSONType,
        nullable=True,
        comment="DEPRECATED – use tokens relationship via Token.root_id",
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

    # Related / similar roots (D7) — manually curated or auto-generated
    related_roots: Mapped[Optional[list]] = mapped_column(
        JSONType,
        nullable=True,
        comment="JSON list of similar/related root strings, e.g. ['\u0633\u0645\u0648', '\u0627\u0633\u0645']",
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

    # ── ORM Relationships ──────────────────────────────────────────
    tokens: Mapped[list["Token"]] = relationship(
        "Token",
        back_populates="root_rel",
        lazy="select",
        order_by="Token.sura, Token.aya, Token.position",
    )
    """All Token rows that share this root (via Token.root_id FK)."""

    def __repr__(self) -> str:
        """String representation of root."""
        return (
            f"<Root(id={self.id}, "
            f"root='{self.root}', "
            f"tokens={self.token_count}, "
            f"meaning='{self.meaning[:30] if self.meaning else None}...')>"
        )
