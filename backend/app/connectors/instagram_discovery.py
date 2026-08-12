from urllib.parse import quote
from app.connectors.http import HttpClient
from app.core.config import get_settings


class InstagramBusinessDiscoveryConnector:
    """Official Business Discovery lookup for an exact public professional username.

    This intentionally does not scrape Instagram search/results pages or automate normal user accounts.
    """
    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    async def lookup(self, username: str) -> dict:
        s = self.settings
        if not s.instagram_discovery_access_token or not s.instagram_discovery_ig_user_id:
            raise RuntimeError("Instagram Business Discovery credentials are missing")
        clean = username.strip().lstrip("@").lower()
        if not clean or len(clean) > 30:
            raise ValueError("invalid Instagram username")
        fields = (
            f"business_discovery.username({clean})"
            "{id,username,name,biography,website,followers_count,media_count,profile_picture_url}"
        )
        url = f"https://graph.facebook.com/{s.instagram_graph_version}/{quote(s.instagram_discovery_ig_user_id)}"
        response = await self.http.request(
            "GET", url, params={"fields": fields, "access_token": s.instagram_discovery_access_token}
        )
        if not response.is_success:
            raise RuntimeError(f"Instagram Business Discovery failed: HTTP {response.status_code} {response.text[:500]}")
        data = response.json()
        return data.get("business_discovery") or {}
