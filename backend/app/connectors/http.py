from __future__ import annotations

import asyncio
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class ResponseTooLarge(ValueError):
    pass


from app.connectors.retry_policy import RetryHint, response_retry_hint

class HttpClient:
    """Loop-local pooled HTTPX client.

    API processes naturally keep one asyncio loop. Celery workers use app.workers.async_runner
    so their loop also survives across tasks, allowing TCP/TLS keep-alive reuse.
    """
    _client: httpx.AsyncClient | None = None
    _loop: asyncio.AbstractEventLoop | None = None

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def _get_client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if self.__class__._client is None or self.__class__._loop is not loop:
            self.__class__._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=min(self.timeout, 8.0)),
                follow_redirects=False,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=30, keepalive_expiry=30.0),
                http2=True,
                headers={"Accept-Encoding": "gzip, br"},
            )
            self.__class__._loop = loop
        return self.__class__._client

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.25, max=4),
        reraise=True,
    )
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        return await self._get_client().request(method, url, **kwargs)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.25, max=4),
        reraise=True,
    )
    async def request_limited(self, method: str, url: str, *, max_bytes: int, **kwargs) -> httpx.Response:
        client = self._get_client()
        async with client.stream(method, url, **kwargs) as response:
            length = response.headers.get("content-length")
            if length and length.isdigit() and int(length) > max_bytes:
                raise ResponseTooLarge(f"response exceeds {max_bytes} bytes")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ResponseTooLarge(f"response exceeds {max_bytes} bytes")
            return httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=bytes(body),
                request=response.request,
                extensions=response.extensions,
            )

    @classmethod
    async def close_pool(cls) -> None:
        if cls._client is not None:
            try:
                await cls._client.aclose()
            finally:
                cls._client = None
                cls._loop = None
