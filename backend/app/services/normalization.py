import re


def normalize_phone(value: str, channel: str) -> str:
    digits = re.sub(r'\D', '', value)
    if channel == "WHATSAPP":
        if digits.startswith("0"):
            digits = "98" + digits[1:]
        if not digits.startswith("98"):
            digits = "98" + digits
    return digits


def normalize_username(value: str) -> str:
    return value.lower().strip().lstrip("@")