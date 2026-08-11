import httpx

from app.connectors.http import HttpClient
from app.core.config import get_settings


class GooglePlacesConnector:
    def __init__(self):
        s = get_settings()
        self.api_key = s.google_places_api_key
        self.language = s.google_places_language

    async def nearby_search(self, query: str, city: str | None = None, max_results: int = 60) -> list[dict]:
        if not self.api_key:
            return []
        client = await HttpClient.get_client()
        location_query = f"{query} {city}" if city else query
        try:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"query": location_query, "language": self.language, "key": self.api_key},
            )
            data = resp.json()
            results = data.get("results", [])[:max_results]
            return [
                {
                    "business_name": r.get("name"),
                    "address": r.get("formatted_address"),
                    "place_id": r.get("place_id"),
                    "rating": r.get("rating"),
                    "types": r.get("types", []),
                }
                for r in results
            ]
        except Exception:
            return []