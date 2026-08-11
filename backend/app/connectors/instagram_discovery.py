import httpx

from app.connectors.http import HttpClient
from app.core.config import get_settings


class InstagramDiscoveryConnector:
    def __init__(self):
        s = get_settings()
        self.access_token = s.instagram_discovery_access_token
        self.ig_user_id = s.instagram_discovery_ig_user_id

    async def search_businesses(self, query: str, max_results: int = 60) -> list[dict]:
        if not self.access_token or not self.ig_user_id:
            return []
        client = await HttpClient.get_client()
        try:
            resp = await client.get(
                f"https://graph.facebook.com/v26.0/ig_hashtag_search",
                params={"user_id": self.ig_user_id, "q": query, "access_token": self.access_token},
            )
            data = resp.json()
            results = data.get("data", [])[:max_results]
            return [{"hashtag_id": r.get("id"), "name": r.get("name")} for r in results]
        except Exception:
            return []

    async def get_business_profile(self, business_id: str) -> dict | None:
        if not self.access_token:
            return None
        client = await HttpClient.get_client()
        try:
            resp = await client.get(
                f"https://graph.facebook.com/v26.0/{business_id}",
                params={"fields": "name,username,biography,website,followers_count,media_count", "access_token": self.access_token},
            )
            return resp.json()
        except Exception:
            return None