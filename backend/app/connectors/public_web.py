import asyncio
import re
import urllib.robotparser
from collections import deque
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from app.connectors.http import HttpClient
from app.services.url_safety import assert_public_url

PHONE_RE = re.compile(r"(?:\+98|0098|0)?9\d{9}|0\d{2,3}[ -]?\d{7,8}")
SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip", ".rar", ".mp4", ".mp3")
SKIP_PATH_PARTS = ("/login", "/signin", "/signup", "/cart", "/checkout", "/account", "/wp-admin")


@dataclass
class PublicBusinessPage:
    url: str
    title: str | None
    phones: list[str]
    instagram: str | None
    telegram: str | None
    whatsapp: str | None


class PublicWebConnector:
    """Robots-aware public web inspection/crawling; never bypasses auth, CAPTCHA or access controls."""
    user_agent = "LeadPlatform/1.0 (+business-contact-indexer)"

    def __init__(self):
        self.http = HttpClient(timeout=15)

    async def _robots(self, seed_url: str) -> urllib.robotparser.RobotFileParser:
        await assert_public_url(seed_url)
        parsed = urlparse(seed_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            robots = await self.http.request_limited("GET", robots_url, max_bytes=512_000, headers={"User-Agent": self.user_agent})
            if robots.is_success:
                rp.parse(robots.text.splitlines())
            else:
                rp.parse([])
        except Exception:
            rp.parse([])
        return rp

    @staticmethod
    def _parse(url: str, html: str) -> tuple[PublicBusinessPage, list[str]]:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        phones = sorted(set(PHONE_RE.findall(text)))[:10]
        links = [urljoin(url, a.get("href", "")) for a in soup.find_all("a") if a.get("href")]
        instagram = next((h for h in links if "instagram.com/" in h), None)
        telegram = next((h for h in links if "t.me/" in h or "telegram.me/" in h), None)
        whatsapp = next((h for h in links if "wa.me/" in h or "api.whatsapp.com/" in h), None)
        page = PublicBusinessPage(
            url=url,
            title=soup.title.string.strip() if soup.title and soup.title.string else None,
            phones=phones,
            instagram=instagram,
            telegram=telegram,
            whatsapp=whatsapp,
        )
        return page, links

    async def fetch_business_page(self, url: str) -> PublicBusinessPage:
        await assert_public_url(url)
        rp = await self._robots(url)
        if not rp.can_fetch(self.user_agent, url):
            raise PermissionError("robots.txt disallows fetching this URL")
        response = await self.http.request_limited("GET", url, max_bytes=2_000_000, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "text/html"):
            raise ValueError("URL did not return HTML")
        page, _ = self._parse(str(response.url), response.text)
        return page

    async def crawl_site(self, seed_url: str, *, max_pages: int = 50, delay_seconds: float = 0.5) -> list[PublicBusinessPage]:
        await assert_public_url(seed_url)
        parsed_seed = urlparse(seed_url)
        origin = parsed_seed.netloc.lower()
        rp = await self._robots(seed_url)
        queue = deque([seed_url])
        visited: set[str] = set()
        business_pages: list[PublicBusinessPage] = []
        max_pages = max(1, min(max_pages, 100))

        while queue and len(visited) < max_pages:
            raw = queue.popleft()
            p = urlparse(raw)
            canonical = urlunparse((p.scheme or parsed_seed.scheme, p.netloc or origin, p.path or "/", "", p.query, ""))
            if canonical in visited or (p.netloc and p.netloc.lower() != origin):
                continue
            lower = canonical.lower()
            if lower.endswith(SKIP_EXT) or any(part in lower for part in SKIP_PATH_PARTS):
                continue
            if not rp.can_fetch(self.user_agent, canonical):
                continue
            await assert_public_url(canonical)
            visited.add(canonical)
            try:
                response = await self.http.request_limited("GET", canonical, max_bytes=2_000_000, headers={"User-Agent": self.user_agent})
                if not response.is_success or "text/html" not in response.headers.get("content-type", "text/html"):
                    continue
                page, links = self._parse(str(response.url), response.text)
                if page.phones or page.instagram or page.telegram or page.whatsapp:
                    business_pages.append(page)
                for link in links:
                    lp = urlparse(link)
                    if lp.scheme in {"http", "https"} and lp.netloc.lower() == origin and link not in visited:
                        queue.append(link)
            finally:
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)
        return business_pages
