import random


def full_jitter_backoff(attempt: int, base_seconds: float = 2.0, cap_seconds: float = 120.0) -> float:
    exp = min(cap_seconds, base_seconds * (2 ** attempt))
    return random.uniform(0, exp)


def parse_retry_after(header_value: str | None) -> int | None:
    if not header_value:
        return None
    try:
        return int(header_value)
    except ValueError:
        return None