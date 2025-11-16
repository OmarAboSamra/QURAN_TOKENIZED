"""Redis caching utilities."""
import hashlib
import json
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from backend.config import get_settings

settings = get_settings()


class CacheManager:
    """
    Redis cache manager for storing frequently accessed data.
    
    Uses hash keys for root lookups and provides TTL-based caching.
    """

    def __init__(self):
        """Initialize cache manager."""
        self._redis: Optional[Redis] = None
        self._enabled = settings.cache_enabled

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._enabled and self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
                print(f"[OK] Redis connected: {settings.redis_url}")
            except Exception as e:
                print(f"⚠ Redis connection failed: {e}")
                self._enabled = False
                self._redis = None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _make_key(self, prefix: str, *args: Any) -> str:
        """Generate cache key from prefix and arguments."""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ":".join(key_parts)

    def _make_hash(self, data: str) -> str:
        """Generate MD5 hash for cache key."""
        return hashlib.md5(data.encode()).hexdigest()

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._enabled or not self._redis:
            return None
        try:
            return await self._redis.get(key)
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        if not self._enabled or not self._redis:
            return False
        try:
            ttl = ttl or settings.cache_ttl
            await self._redis.setex(key, ttl, value)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def get_json(self, key: str) -> Optional[dict | list]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: dict | list,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set JSON value in cache."""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, ttl)
        except (TypeError, ValueError) as e:
            print(f"JSON serialization error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._enabled or not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._enabled or not self._redis:
            return 0
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0

    # Specialized caching methods
    async def get_root(self, normalized_word: str) -> Optional[str]:
        """Get cached root for a normalized word."""
        key = self._make_key("root", self._make_hash(normalized_word))
        return await self.get(key)

    async def set_root(self, normalized_word: str, root: str) -> bool:
        """Cache root for a normalized word."""
        key = self._make_key("root", self._make_hash(normalized_word))
        return await self.set(key, root, ttl=86400)  # 24 hours

    async def get_verse(self, sura: int, aya: int) -> Optional[dict]:
        """Get cached verse data."""
        key = self._make_key("verse", sura, aya)
        return await self.get_json(key)

    async def set_verse(self, sura: int, aya: int, data: dict) -> bool:
        """Cache verse data."""
        key = self._make_key("verse", sura, aya)
        return await self.set_json(key, data, ttl=3600)

    async def invalidate_verse(self, sura: int, aya: int) -> bool:
        """Invalidate cached verse."""
        key = self._make_key("verse", sura, aya)
        return await self.delete(key)

    async def get_tokens_by_root(self, root: str, page: int = 1) -> Optional[list]:
        """Get cached tokens for a root."""
        key = self._make_key("tokens_root", root, page)
        return await self.get_json(key)

    async def set_tokens_by_root(
        self,
        root: str,
        page: int,
        tokens: list,
    ) -> bool:
        """Cache tokens for a root."""
        key = self._make_key("tokens_root", root, page)
        return await self.set_json(key, tokens, ttl=1800)  # 30 minutes


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
