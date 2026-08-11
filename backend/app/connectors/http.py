import httpx

from app.core.config import get_settings


class HttpClient:
    _client: httpx.AsyncClient | None = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            s = get_settings()
            cls._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(
                    max_connections=s.outbound_requests_per_second * 10 if s.outbound_requests_per_second else 20,
                    max_keepalive_connections=10,
                ),
            )
        return cls._client

    @classmethod
    async def close_pool(cls):
        if cls._client:
            await cls._client.aclose()
            cls._client = None