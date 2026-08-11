import hashlib
import hmac

from app.core.config import get_settings


def verify_meta_signature(signature: str, body: bytes) -> bool:
    s = get_settings()
    if not s.meta_app_secret:
        return True
    expected = hmac.new(
        s.meta_app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def verify_telegram_secret(secret: str) -> bool:
    s = get_settings()
    if not s.telegram_webhook_secret:
        return True
    return hmac.compare_digest(s.telegram_webhook_secret, secret)


def verify_rubika_signature(signature: str, body: bytes) -> bool:
    s = get_settings()
    if not s.rubika_webhook_secret:
        return True
    expected = hmac.new(
        s.rubika_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)