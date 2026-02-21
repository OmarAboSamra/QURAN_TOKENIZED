"""
Repository package — database query layer.

Exports BaseRepository (generic CRUD) and TokenRepository
(domain-specific Qur'an token queries).
"""
from backend.repositories.base import BaseRepository
from backend.repositories.token_repository import TokenRepository

__all__ = ["BaseRepository", "TokenRepository"]
