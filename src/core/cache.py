"""Cache abstraction and implementations."""

import json
from abc import ABC, abstractmethod
from typing import Any

from redis.asyncio import Redis

from core.config import logger


class AbstractCache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, expire: int | None = None) -> None:
        """Set value with optional expiration in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value by key."""
        pass

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        pass

    async def get_json(self, key: str) -> Any | None:
        """Get JSON value by key."""
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON for key: {key}")
            return None

    async def set_json(self, key: str, value: Any, expire: int | None = None) -> None:
        """Set JSON value with optional expiration."""
        json_value = json.dumps(value, default=str)
        await self.set(key, json_value, expire)


class RedisCache(AbstractCache):
    """Redis implementation of cache."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        value = await self.redis.get(key)
        if value is None:
            return None
        # Decode bytes to str if needed (fakeredis returns bytes)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        # Ensure we always return str (production Redis with decode_responses=True)
        return str(value)

    async def set(self, key: str, value: str, expire: int | None = None) -> None:
        """Set value with optional expiration in seconds."""
        if expire:
            await self.redis.setex(key, expire, value)
        else:
            await self.redis.set(key, value)

    async def delete(self, key: str) -> None:
        """Delete value by key."""
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern using pipeline for optimal performance."""
        deleted_count = 0
        batch_size = 500

        pipeline = self.redis.pipeline()
        batch_count = 0

        async for key in self.redis.scan_iter(match=pattern, count=1000):
            pipeline.delete(key)
            batch_count += 1

            if batch_count >= batch_size:
                await pipeline.execute()
                deleted_count += batch_count
                pipeline = self.redis.pipeline()
                batch_count = 0

        if batch_count > 0:
            await pipeline.execute()
            deleted_count += batch_count

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} keys matching pattern: {pattern}")
