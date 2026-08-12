from datetime import timedelta

import httpx
import jwt
import pytest
from pydantic import ValidationError

from app.connectors.retry_policy import response_retry_hint
from app.core.config import get_settings
from app.core.security import ALGORITHM, create_token, decode_token
from app.schemas.campaigns import CampaignCreate
from app.services.reply_classifier import classify_reply, classify_reply_detailed
from app.services.url_safety import assert_public_url


def test_opt_out_has_precedence_over_commercial_terms():
    result = classify_reply_detailed("قیمت خوبه ولی لطفاً دیگه پیام ندید")
    assert result.label == "OPT_OUT"
    assert result.confidence >= 0.99
    assert result.engine == "rules-v2"


def test_not_interested_has_precedence_over_price_term():
    assert classify_reply("قیمت مهم نیست، فعلاً نیاز ندارم") == "NOT_INTERESTED"


def test_persian_arabic_character_normalization():
    assert classify_reply("لطفا شرايط همكاري را بفرستید") == "PURCHASE_INTENT"


def test_followup_later_is_not_hot():
    assert classify_reply("ماه بعد تماس بگیرید") == "FOLLOW_UP_LATER"


def test_bare_price_is_commercial_signal_but_lower_confidence():
    result = classify_reply_detailed("قیمت؟")
    assert result.label == "PURCHASE_INTENT"
    assert 0.70 <= result.confidence < 0.90


def test_campaign_channels_normalize_and_deduplicate():
    payload = CampaignCreate(name="A campaign", channels=[" whatsapp ", "WHATSAPP", "telegram"], message_template="hello")
    assert payload.channels == ["WHATSAPP", "TELEGRAM"]


def test_campaign_rejects_unsupported_channel():
    with pytest.raises(ValidationError):
        CampaignCreate(name="A campaign", channels=["carrier_pigeon"], message_template="hello")


def test_access_token_round_trip_and_wrong_type_rejected():
    token = create_token("user-1", "access", timedelta(minutes=5), session_id="session-1")
    decoded = decode_token(token, "access")
    assert decoded.subject == "user-1"
    assert decoded.session_id == "session-1"
    with pytest.raises(ValueError):
        decode_token(token, "refresh")


def test_jwt_algorithm_is_hard_coded_not_header_selected():
    s = get_settings()
    payload = {
        "sub": "u", "type": "access", "sid": "s", "jti": "j",
        "iat": 2_000_000_000, "nbf": 1, "exp": 4_000_000_000,
        "iss": s.jwt_issuer, "aud": s.jwt_audience,
    }
    hs256 = jwt.encode(payload, s.secret_key, algorithm="HS256")
    with pytest.raises(ValueError):
        decode_token(hs256, "access")
    assert ALGORITHM == "HS512"


def test_retry_hint_honors_retry_after_header():
    r = httpx.Response(429, headers={"Retry-After": "17"}, request=httpx.Request("POST", "https://example.test"))
    hint = response_retry_hint(r)
    assert hint.retryable and hint.retry_after_seconds == 17


def test_retry_hint_reads_telegram_retry_after_body():
    r = httpx.Response(429, json={"parameters": {"retry_after": 9}}, request=httpx.Request("POST", "https://example.test"))
    hint = response_retry_hint(r)
    assert hint.retryable and hint.retry_after_seconds == 9


def test_5xx_retryable_4xx_not_retryable():
    five = response_retry_hint(httpx.Response(503, request=httpx.Request("GET", "https://example.test")))
    four = response_retry_hint(httpx.Response(400, request=httpx.Request("GET", "https://example.test")))
    assert five.retryable
    assert not four.retryable


@pytest.mark.asyncio
async def test_ssrf_guard_rejects_ipv6_loopback():
    with pytest.raises(ValueError):
        await assert_public_url("http://[::1]/private")
