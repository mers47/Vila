from __future__ import annotations

import asyncio
import weakref

import redis.asyncio as redis

from app.core.config import get_settings

# Redis asyncio pools are loop-affine in practice. Keep one client per event loop so API
# requests and Celery's persistent worker loop reuse TCP connections instead of reconnecting
# on every rate-limit/circuit check.
_clients: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, redis.Redis]" = weakref.WeakKeyDictionary()


def redis_client() -> redis.Redis:
    loop = asyncio.get_running_loop()
    client = _clients.get(loop)
    if client is None:
        client = redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=2,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        _clients[loop] = client
    return client


async def close_redis_pool() -> None:
    loop = asyncio.get_running_loop()
    client = _clients.pop(loop, None)
    if client is not None:
        await client.aclose()
