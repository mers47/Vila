import redis.asyncio as aioredis

from app.core.config import get_settings

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = aioredis.from_url(s.redis_url, max_connections=20, decode_responses=True)
    return _pool


async def close_redis_pool():
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None