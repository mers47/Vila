import httpx
from urllib.parse import urlparse

from app.connectors.http import HttpClient


class PublicWebConnector:
    async def scrape_business_info(self, url: str) -> dict | None:
        client = await HttpClient.get_client()
        try:
            resp = await client.get(url, follow_redirects=True, timeout=15.0)
            if resp.status_code != 200:
                return None
            html = resp.text.lower()
            domain = urlparse(url).netloc

            title = ""
            if "<title>" in html:
                title = html.split("<title>")[1].split("</title>")[0] if "</title>" in html.split("<title>")[1] else ""

            return {
                "url": url,
                "domain": domain,
                "title": title.strip()[:255],
                "http_status": resp.status_code,
                "content_length": len(html),
            }
        except Exception:
            return None

    async def extract_contact_info(self, html: str) -> dict:
        import re
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)))
        phones = list(set(re.findall(r'(?:0\d{2,3}[-\s]?)?\d{7,10}', html)))
        return {"emails": emails[:10], "phones": phones[:10]}