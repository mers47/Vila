from __future__ import annotations

import math
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.redis_pool import redis_client

# Conservative application-side budgets. Provider Retry-After remains authoritative and
# account/tier-specific limits can be made stricter at deployment time.
LIMITS = {
    "WHATSAPP": (5.0, 10.0),
    "INSTAGRAM": (5.0, 10.0),
    "TELEGRAM": (10.0, 20.0),
    "EITAA": (2.0, 4.0),
    "RUBIKA": (2.0, 4.0),
}

_BUCKET_LUA = r'''
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then tokens = capacity end
if ts == nil then ts = now_ms end
local elapsed = math.max(0, now_ms - ts)
tokens = math.min(capacity, tokens + (elapsed / 1000.0) * rate)
local allowed = 0
local retry_ms = 0
if tokens >= 1.0 then
  tokens = tokens - 1.0
  allowed = 1
else
  retry_ms = math.ceil(((1.0 - tokens) / rate) * 1000.0)
end
redis.call('HSET', key, 'tokens', tokens, 'ts', now_ms)
redis.call('PEXPIRE', key, math.ceil((capacity / rate) * 3000.0))
return {allowed, retry_ms}
'''


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    retry_after_seconds: int = 0


async def provider_budget(channel: str) -> RateDecision:
    channel = channel.upper()
    rate, capacity = LIMITS.get(channel, (1.0, 2.0))
    client = redis_client()
    allowed, retry_ms = await client.eval(
        _BUCKET_LUA,
        1,
        f"provider-bucket:{channel}",
        int(time.time() * 1000),
        rate,
        capacity,
    )
    return RateDecision(bool(int(allowed)), max(0, math.ceil(int(retry_ms) / 1000)))


async def circuit_delay(channel: str) -> int:
    ttl = await redis_client().ttl(f"provider-circuit-open:{channel.upper()}")
    return max(0, int(ttl)) if ttl and int(ttl) > 0 else 0


async def record_provider_success(channel: str) -> None:
    await redis_client().delete(
        f"provider-failures:{channel.upper()}",
        f"provider-circuit-open:{channel.upper()}",
    )


async def record_provider_failure(channel: str) -> int:
    s = get_settings()
    channel = channel.upper()
    client = redis_client()
    failures = await client.incr(f"provider-failures:{channel}")
    await client.expire(f"provider-failures:{channel}", max(60, s.provider_circuit_open_seconds * 5))
    if int(failures) >= s.provider_circuit_failures:
        await client.set(f"provider-circuit-open:{channel}", "1", ex=s.provider_circuit_open_seconds)
        return s.provider_circuit_open_seconds
    return 0


async def provider_slot(channel: str) -> bool:
    return (await provider_budget(channel)).allowed
