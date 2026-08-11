import pytest
from datetime import timedelta

from app.core.security import hash_password, verify_password, create_token, decode_token, DecodedToken
from app.services.normalization import normalize_phone, normalize_username
from app.services.policy import can_send
from app.services.reply_classifier import classify_reply
from app.services.url_safety import is_safe_url
from app.services.templates import render_template


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "StrongP@ssw0rd!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed)
        assert not verify_password("wrong", hashed)

    def test_hash_is_unique(self):
        pw = "test1234"
        assert hash_password(pw) != hash_password(pw)


class TestTokenCreation:
    def test_create_and_decode(self):
        token = create_token("user-1", "access", timedelta(minutes=15), session_id="sess-1")
        decoded = decode_token(token, "access")
        assert decoded.subject == "user-1"
        assert decoded.token_type == "access"
        assert decoded.session_id == "sess-1"

    def test_wrong_type_fails(self):
        token = create_token("user-1", "access", timedelta(minutes=15), session_id="sess-1")
        with pytest.raises(ValueError, match="invalid token type"):
            decode_token(token, "refresh")


class TestNormalization:
    def test_phone_whatsapp(self):
        assert normalize_phone("09121234567", "WHATSAPP") == "989121234567"
        assert normalize_phone("+989121234567", "WHATSAPP") == "989121234567"

    def test_username(self):
        assert normalize_username("@TestUser") == "testuser"
        assert normalize_username("  TestUser  ") == "testuser"


class TestPolicy:
    def test_can_send_valid(self):
        ok, reason = can_send("WHATSAPP", "IMPLIED", True, False, True)
        assert ok
        assert reason is None

    def test_can_send_suppressed(self):
        ok, reason = can_send("WHATSAPP", "IMPLIED", True, True, True)
        assert not ok
        assert reason == "suppressed"

    def test_can_send_opted_out(self):
        ok, reason = can_send("WHATSAPP", "OPTED_OUT", True, False, True)
        assert not ok
        assert reason == "opted_out"


class TestReplyClassifier:
    def test_optout(self):
        label, conf = classify_reply("لطفا لغو کنید")
        assert label == "OPTOUT"
        assert conf >= 70

    def test_positive(self):
        label, conf = classify_reply("بله موافقم")
        assert label == "POSITIVE"

    def test_neutral(self):
        label, conf = classify_reply("سلام")
        assert label == "NEUTRAL"


class TestUrlSafety:
    def test_safe_url(self):
        assert is_safe_url("https://example.com")

    def test_blocked_localhost(self):
        assert not is_safe_url("http://localhost:8000")

    def test_blocked_internal(self):
        assert not is_safe_url("http://127.0.0.1")


class TestTemplates:
    def test_render_persian(self):
        result = render_template("intro", "fa", business_name="تست", company_name="شرکت ما")
        assert "تست" in result
        assert "شرکت ما" in result