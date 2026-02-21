"""
Shared SQLAlchemy custom types for model definitions.

Provides a JSONType that automatically uses JSONB on PostgreSQL
(with native indexing/querying) or serializes to Text on SQLite.
This lets the same ORM models work on both databases without changes.
"""
import json

from sqlalchemy import Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL JSONB and SQLite Text."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value
