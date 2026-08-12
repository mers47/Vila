from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: str = "development"
    app_name: str = "Lead Acquisition Platform"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    jwt_issuer: str = "lead-platform"
    jwt_audience: str = "lead-platform-api"
    auth_login_attempts_per_15m: int = 10
    cookie_secure: bool = False

    database_url: str = "postgresql+asyncpg://lead:lead@postgres:5432/lead"
    redis_url: str = "redis://redis:6379/0"
    frontend_origin: str = "http://localhost:3000"

    google_places_api_key: str | None = None
    google_places_language: str = "fa"

    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_graph_version: str = "v26.0"

    instagram_access_token: str | None = None
    instagram_business_account_id: str | None = None
    instagram_graph_version: str = "v26.0"
    instagram_discovery_access_token: str | None = None
    instagram_discovery_ig_user_id: str | None = None

    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    eitaa_app_token: str | None = None
    rubika_bot_token: str | None = None
    rubika_webhook_secret: str | None = None

    webhook_verify_token: str | None = None
    meta_app_secret: str | None = None
    outbound_requests_per_second: float = 2.0
    provider_circuit_failures: int = 5
    provider_circuit_open_seconds: int = 60
    outbox_lease_seconds: int = 180
    outbox_batch_size: int = 100
    outbox_max_attempts: int = 8
    outbox_retention_days: int = 14
    revoked_session_retention_days: int = 30
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 5
    db_pool_recycle: int = 1800
    db_statement_timeout_ms: int = 15000
    db_idle_in_transaction_timeout_ms: int = 30000


@lru_cache
def get_settings() -> Settings:
    return Settings()