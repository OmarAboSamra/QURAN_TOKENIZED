"""ORM model for Arabic roots."""
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import DateTime, Index, Integer, String, Text, TypeDecorator, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

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
