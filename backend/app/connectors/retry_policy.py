from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class RetryHint:
    retryable: bool
    retry_after_seconds: int | None = None


def response_retry_hint(response: httpx.Response) -> RetryHint:
    status = response.status_code
    retryable = status == 429 or 500 <= status <= 599
    retry_after = None
    header = response.headers.get("retry-after")
    if header and header.isdigit():
        retry_after = max(1, min(int(header), 86400))
    if status == 429 and retry_after is None:
        try:
            data = response.json()
            value = ((data.get("parameters") or {}).get("retry_after")) if isinstance(data, dict) else None
            if value is not None:
                retry_after = max(1, min(int(value), 86400))
        except Exception:
            pass
    return RetryHint(retryable, retry_after)
