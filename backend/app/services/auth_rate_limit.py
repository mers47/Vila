from __future__ import annotations

import hashlib

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.services.redis_pool import redis_client


async def check_login_budget(identity: str, ip: str) -> tuple[bool, int]:
    """Fixed-window login limiter. Returns (allowed, retry_after_seconds).

    The Redis key contains only SHA-256 material, not raw email/IP data. Redis connections
    are pooled per process/event-loop rather than created for every login attempt.
    """
    s = get_settings()
    digest = hashlib.sha256(f"{identity.lower()}|{ip}".encode("utf-8")).hexdigest()
    key = f"auth-login:{digest}"
    client = redis_client()
    try:
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 900, nx=True)
            count, _ = await pipe.execute()
            ttl = await client.ttl(key)
        return int(count) <= s.auth_login_attempts_per_15m, max(1, int(ttl))
    except RedisError:
        if s.environment.lower() == "production":
            return False, 30
        return True, 0
