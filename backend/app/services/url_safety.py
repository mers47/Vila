import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlparse


def social_handle(url: str | None) -> str | None:
    if not url:
        return None
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[0].lstrip("@") or None


def whatsapp_number(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if "wa.me" in parsed.netloc:
        digits = re.sub(r"\D", "", parsed.path)
        return f"+{digits}" if digits else None
    m = re.search(r"(?:phone=|send\?phone=)(\+?\d+)", url)
    return m.group(1) if m else None


async def assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("valid public http/https URL required")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise ValueError("local/private hosts are not allowed")
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise ValueError("hostname could not be resolved") from exc
        addresses = list({ipaddress.ip_address(info[4][0]) for info in infos})
    if not addresses:
        raise ValueError("hostname has no addresses")
    for ip in addresses:
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_reserved,
                ip.is_multicast, ip.is_unspecified)):
            raise ValueError("private/link-local/reserved destinations are not allowed")
