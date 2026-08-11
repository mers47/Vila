from app.core.config import Settings


def validate_production_settings(s: Settings):
    if s.environment != "production":
        return
    errors = []

    if len(s.secret_key) < 32:
        errors.append("SECRET_KEY must be at least 32 characters in production")
    if not s.database_url or "asyncpg" not in s.database_url:
        errors.append("DATABASE_URL must use asyncpg driver")
    if not s.redis_url:
        errors.append("REDIS_URL is required")
    if not s.cookie_secure:
        errors.append("COOKIE_SECURE must be true in production")
    if s.frontend_origin in ("http://localhost:3000", "http://localhost"):
        errors.append("FRONTEND_ORIGIN must be set to real domain in production")

    if errors:
        msg = "Production settings validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(msg)