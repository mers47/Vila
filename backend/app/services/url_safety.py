from urllib.parse import urlparse


BLOCKED_DOMAINS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "internal", "metadata"}


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname in BLOCKED_DOMAINS or hostname.endswith(".local"):
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        return True
    except Exception:
        return False