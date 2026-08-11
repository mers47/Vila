import time
from collections import defaultdict

from app.core.config import get_settings

_provider_failure_counts: dict[str, int] = {}
_provider_last_failure: dict[str, float] = {}
_token_buckets: dict[str, tuple[float, float]] = {}


def _bucket_key(provider: str) -> str:
    return f"outbound:{provider}"


async def provider_budget(provider: str) -> bool:
    s = get_settings()
    now = time.monotonic()
    key = _bucket_key(provider)
    tokens, last_refill = _token_buckets.get(key, (s.outbound_requests_per_second, now))
    elapsed = now - last_refill
    tokens = min(s.outbound_requests_per_second, tokens + elapsed * s.outbound_requests_per_second)
    if tokens < 1.0:
        _token_buckets[key] = (tokens, now)
        return False
    _token_buckets[key] = (tokens - 1.0, now)
    return True


async def circuit_delay(provider: str) -> float:
    s = get_settings()
    count = _provider_failure_counts.get(provider, 0)
    if count < s.provider_circuit_failures:
        return 0.0
    last = _provider_last_failure.get(provider, 0)
    elapsed = time.monotonic() - last
    if elapsed >= s.provider_circuit_open_seconds:
        _provider_failure_counts[provider] = 0
        return 0.0
    return s.provider_circuit_open_seconds - elapsed


async def record_provider_success(provider: str):
    _provider_failure_counts[provider] = 0


async def record_provider_failure(provider: str):
    _provider_failure_counts[provider] = _provider_failure_counts.get(provider, 0) + 1
    _provider_last_failure[provider] = time.monotonic()