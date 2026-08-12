from __future__ import annotations

import httpx

from app.connectors.base import SendResult
from app.connectors.retry_policy import response_retry_hint


def response_latency_ms(response: httpx.Response) -> int | None:
    try:
        return max(0, int(response.elapsed.total_seconds() * 1000))
    except Exception:
        return None


def success_result(response: httpx.Response, external_message_id: str | None) -> SendResult:
    return SendResult(
        True,
        external_message_id,
        http_status=response.status_code,
        latency_ms=response_latency_ms(response),
    )


def failure_result(response: httpx.Response, *, detail: str | None = None, code: str | None = None) -> SendResult:
    hint = response_retry_hint(response)
    return SendResult(
        False,
        error_code=code or str(response.status_code),
        error_detail=(detail if detail is not None else response.text[:1000]),
        http_status=response.status_code,
        retryable=hint.retryable,
        retry_after_seconds=hint.retry_after_seconds,
        latency_ms=response_latency_ms(response),
    )
