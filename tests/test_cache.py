"""Tests for cache implementation."""

import pytest
from redis.asyncio import Redis

from core.cache import RedisCache


@pytest.fixture
async def redis_client():
    """Create test Redis client using fakeredis."""
    try:
        from fakeredis import aioredis as fake_aioredis
    except ImportError:
        pytest.skip("fakeredis not installed")

    client = fake_aioredis.FakeRedis()
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
def cache(redis_client: Redis) -> RedisCache:
    """Create cache instance with test Redis client."""
    return RedisCache(redis_client)


@pytest.mark.asyncio
class TestRedisCache:
    """Test Redis cache implementation."""

    async def test_get_set(self, cache: RedisCache):
        """Test basic get/set operations."""
        await cache.set("test_key", "test_value")
        value = await cache.get("test_key")
        assert value == "test_value"

    async def test_set_with_expiration(self, cache: RedisCache):
        """Test set with expiration time."""
        await cache.set("expiring_key", "value", expire=10)
        value = await cache.get("expiring_key")
        assert value == "value"

    async def test_get_nonexistent_key(self, cache: RedisCache):
        """Test get on nonexistent key returns None."""
        value = await cache.get("nonexistent")
        assert value is None

    async def test_delete(self, cache: RedisCache):
        """Test delete operation."""
        await cache.set("to_delete", "value")
        await cache.delete("to_delete")
        value = await cache.get("to_delete")
        assert value is None

    async def test_get_json(self, cache: RedisCache):
        """Test JSON get operation."""
        data = {"key": "value", "number": 42}
        await cache.set_json("json_key", data)
        result = await cache.get_json("json_key")
        assert result == data

    async def test_get_json_nonexistent(self, cache: RedisCache):
        """Test JSON get on nonexistent key returns None."""
        result = await cache.get_json("nonexistent")
        assert result is None

    async def test_set_json_with_expiration(self, cache: RedisCache):
        """Test JSON set with expiration."""
        data = {"test": "data"}
        await cache.set_json("json_key", data, expire=10)
        result = await cache.get_json("json_key")
        assert result == data


@pytest.mark.asyncio
class TestDeletePattern:
    """Test delete_pattern method with various scenarios."""

    async def test_delete_pattern_basic(self, cache: RedisCache):
        """Test basic pattern deletion."""
        # Create test keys
        await cache.set("analytics:summary:1", "data1")
        await cache.set("analytics:summary:2", "data2")
        await cache.set("analytics:funnel:1", "data3")
        await cache.set("other:key", "data4")

        # Delete analytics:summary:* pattern
        await cache.delete_pattern("analytics:summary:*")

        # Check that only matching keys were deleted
        assert await cache.get("analytics:summary:1") is None
        assert await cache.get("analytics:summary:2") is None
        assert await cache.get("analytics:funnel:1") == "data3"
        assert await cache.get("other:key") == "data4"

    async def test_delete_pattern_no_matches(self, cache: RedisCache):
        """Test delete_pattern when no keys match."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Delete pattern that doesn't match anything
        await cache.delete_pattern("nonexistent:*")

        # All keys should remain
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

    async def test_delete_pattern_all_keys(self, cache: RedisCache):
        """Test deleting all keys with * pattern."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        await cache.delete_pattern("*")

        # All keys should be deleted
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    async def test_delete_pattern_batched_deletion(self, cache: RedisCache):
        """Test that batched deletion works correctly with many keys."""
        # Create 1000 keys to test batch processing
        for i in range(1000):
            await cache.set(f"batch:key:{i}", f"value{i}")

        # Create some keys that shouldn't be deleted
        await cache.set("other:key:1", "keep1")
        await cache.set("other:key:2", "keep2")

        # Delete batch:* pattern
        await cache.delete_pattern("batch:*")

        # Verify batch keys are deleted
        for i in range(1000):
            value = await cache.get(f"batch:key:{i}")
            assert value is None, f"Key batch:key:{i} should be deleted"

        # Verify other keys remain
        assert await cache.get("other:key:1") == "keep1"
        assert await cache.get("other:key:2") == "keep2"

    async def test_delete_pattern_complex_pattern(self, cache: RedisCache):
        """Test delete with complex patterns."""
        # Create test keys
        await cache.set("analytics:org:123:summary", "data1")
        await cache.set("analytics:org:123:funnel", "data2")
        await cache.set("analytics:org:456:summary", "data3")
        await cache.set("cache:org:123:data", "data4")

        # Delete analytics for org 123
        await cache.delete_pattern("analytics:org:123:*")

        # Check correct keys were deleted
        assert await cache.get("analytics:org:123:summary") is None
        assert await cache.get("analytics:org:123:funnel") is None
        assert await cache.get("analytics:org:456:summary") == "data3"
        assert await cache.get("cache:org:123:data") == "data4"

    async def test_delete_pattern_organization_isolation(self, cache: RedisCache):
        """Test that pattern deletion respects organization isolation."""
        # Organization 1 cache
        await cache.set("analytics:summary:1:30", "org1_summary")
        await cache.set("analytics:funnel:1", "org1_funnel")

        # Organization 2 cache
        await cache.set("analytics:summary:2:30", "org2_summary")
        await cache.set("analytics:funnel:2", "org2_funnel")

        # Invalidate org 1 analytics (similar to real usage in deals.py)
        await cache.delete_pattern("analytics:*:1*")

        # Org 1 cache should be cleared
        assert await cache.get("analytics:summary:1:30") is None
        assert await cache.get("analytics:funnel:1") is None

        # Org 2 cache should remain
        assert await cache.get("analytics:summary:2:30") == "org2_summary"
        assert await cache.get("analytics:funnel:2") == "org2_funnel"

    async def test_delete_pattern_empty_cache(self, cache: RedisCache):
        """Test delete_pattern on empty cache doesn't error."""
        # Should not raise error on empty cache
        await cache.delete_pattern("any:pattern:*")

        # Verify nothing broke
        await cache.set("test", "value")
        assert await cache.get("test") == "value"
