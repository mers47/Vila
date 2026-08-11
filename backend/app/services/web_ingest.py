from app.connectors.public_web import PublicWebConnector
from app.services.url_safety import is_safe_url


async def ingest_website(url: str) -> dict | None:
    if not is_safe_url(url):
        return None
    connector = PublicWebConnector()
    return await connector.scrape_business_info(url)