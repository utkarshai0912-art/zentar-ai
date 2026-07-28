"""
Zentar Intelligence — Redis Client

Async Redis connection management for caching, rate limiting, and pub/sub.
"""

import json
from typing import Any, Dict, Optional

from redis import asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

# Redis connection pool
redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create the Redis connection."""
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            max_connections=settings.REDIS_POOL_SIZE,
        )
    return redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None


# --- Cache Helpers ---

async def cache_get(key: str) -> Optional[str]:
    """Get a value from cache."""
    redis = await get_redis()
    return await redis.get(key)


async def cache_set(
    key: str,
    value: str,
    ttl_seconds: int = 300,
) -> None:
    """Set a value in cache with TTL."""
    redis = await get_redis()
    await redis.setex(key, ttl_seconds, value)


async def cache_get_json(key: str) -> Optional[Any]:
    """Get and deserialize a JSON value from cache."""
    data = await cache_get(key)
    return json.loads(data) if data else None


async def cache_set_json(
    key: str,
    value: Any,
    ttl_seconds: int = 300,
) -> None:
    """Serialize and cache a JSON value."""
    await cache_set(key, json.dumps(value), ttl_seconds)


async def cache_delete(key: str) -> None:
    """Delete a key from cache."""
    redis = await get_redis()
    await redis.delete(key)


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern."""
    redis = await get_redis()
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break


# --- Rate Limiting ---

async def check_rate_limit(
    key: str,
    max_requests: int = 100,
    window_seconds: int = 60,
) -> tuple[bool, Dict[str, Any]]:
    """
    Sliding window rate limit check using Redis sorted sets.
    Returns (allowed, headers_dict).
    """
    if not settings.RATE_LIMIT_ENABLED:
        return True, {}

    redis = await get_redis()
    now = __import__("time").time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds * 2)
    _, count, _, _ = await pipe.execute()

    allowed = count <= max_requests
    return allowed, {
        "X-RateLimit-Limit": str(max_requests),
        "X-RateLimit-Remaining": str(max(0, max_requests - count)),
        "X-RateLimit-Reset": str(int(now + window_seconds)),
    }


# --- Pub/Sub ---

async def publish(channel: str, message: Any) -> None:
    """Publish a message to a Redis channel."""
    redis = await get_redis()
    payload = json.dumps(message) if not isinstance(message, str) else message
    await redis.publish(channel, payload)
