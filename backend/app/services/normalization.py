import re
from urllib.parse import urlparse


def normalize_phone(value: str, default_region: str = "IR") -> str:
    raw = re.sub(r"[^0-9+]", "", value.strip())
    if default_region.upper() == "IR":
        digits = re.sub(r"\D", "", raw)
        if digits.startswith("0098"):
            digits = digits[4:]
        elif digits.startswith("98"):
            digits = digits[2:]
        if digits.startswith("0"):
            digits = digits[1:]
        if len(digits) in {10, 11}:
            return "+98" + digits
    if raw.startswith("00"):
        return "+" + raw[2:]
    return raw


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def normalize_handle(value: str) -> str:
    return value.strip().lower().lstrip("@").rstrip("/")


def normalize_contact(channel: str, value: str) -> str:
    channel = channel.upper()
    if channel in {"WHATSAPP", "PHONE"}:
        return normalize_phone(value)
    if channel == "WEB":
        return normalize_url(value)
    return normalize_handle(value)
