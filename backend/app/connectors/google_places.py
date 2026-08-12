from app.connectors.http import HttpClient
from app.core.config import get_settings


class GooglePlacesConnector:
    base_url = "https://places.googleapis.com/v1/places:searchText"

    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    async def text_search(self, query: str, *, max_results: int = 60) -> list[dict]:
        if not self.settings.google_places_api_key:
            raise RuntimeError("GOOGLE_PLACES_API_KEY is not configured")
        max_results = max(1, min(max_results, 60))
        headers = {
            "X-Goog-Api-Key": self.settings.google_places_api_key,
            "X-Goog-FieldMask": ",".join([
                "places.id", "places.displayName", "places.formattedAddress",
                "places.nationalPhoneNumber", "places.internationalPhoneNumber",
                "places.websiteUri", "places.primaryType", "places.businessStatus", "nextPageToken"
            ]),
            "Content-Type": "application/json",
        }
        results: list[dict] = []
        page_token: str | None = None
        while len(results) < max_results:
            payload = {
                "textQuery": query,
                "languageCode": self.settings.google_places_language,
                "pageSize": min(20, max_results - len(results)),
            }
            if page_token:
                payload["pageToken"] = page_token
            response = await self.http.request("POST", self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("places", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return results[:max_results]
