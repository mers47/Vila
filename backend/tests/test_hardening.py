import pytest

from app.core.config import get_settings


class TestSettings:
    def test_secret_key_min_length(self):
        s = get_settings()
        assert len(s.secret_key) >= 32 or s.environment != "production"

    def test_oauth_scopes_present(self):
        s = get_settings()
        assert isinstance(s.jwt_issuer, str) and len(s.jwt_issuer) > 0
        assert isinstance(s.jwt_audience, str) and len(s.jwt_audience) > 0


class TestSecurityConfig:
    def test_argon2_params(self):
        from app.core.security import _password_hasher
        assert _password_hasher.time_cost >= 2
        assert _password_hasher.memory_cost >= 65536

    def test_algorithm_is_hs512(self):
        from app.core.security import ALGORITHM
        assert ALGORITHM == "HS512"


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_token_bucket_allows_tokens(self):
        from app.services.rate_limit import provider_budget
        result = await provider_budget("WHATSAPP")
        assert result is True

    @pytest.mark.asyncio
    async def test_circuit_starts_closed(self):
        from app.services.rate_limit import circuit_delay, record_provider_success
        await record_provider_success("WHATSAPP")
        delay = await circuit_delay("WHATSAPP")
        assert delay == 0.0


class TestStartup:
    def test_production_validation(self):
        from app.core.startup import validate_production_settings
        from app.core.config import Settings
        s = Settings(
            environment="production", secret_key="short", database_url="postgresql://...",
            redis_url="", cookie_secure=False, frontend_origin="http://localhost:3000"
        )
        with pytest.raises(RuntimeError):
            validate_production_settings(s)


class TestWebhookSecurity:
    def test_meta_signature_no_secret(self):
        from app.core.webhook_security import verify_meta_signature
        assert verify_meta_signature("anything", b"body") is True

    def test_telegram_secret_no_secret(self):
        from app.core.webhook_security import verify_telegram_secret
        assert verify_telegram_secret("anything") is True