from app.core.config import get_settings
from app.services.redis_pool import get_redis


async def check_login_rate_limit(email: str) -> bool:
    s = get_settings()
    redis = await get_redis()
    key = f"auth:login_attempts:{email}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 900)
    return current <= s.auth_login_attempts_per_15m