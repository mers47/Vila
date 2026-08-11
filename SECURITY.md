# Security Policy

## Reporting a Vulnerability
**Do not open a public issue.** Instead, send details to the maintainer privately.

## Authentication & Secrets
- All secrets are injected via environment variables; never commit `.env` files.
- `SECRET_KEY` must be ≥ 32 random characters in production.
- JWT tokens use HS512 with audience + issuer validation.
- Password hashing via Argon2id (time_cost=3, memory_cost=65536, parallelism=2).

## API Hardening
- CSRF-like cookie guard: cookie-based sessions require matching `Origin` header on unsafe methods.
- Rate limiting on auth endpoints (token-bucket, configurable).
- Session rotation on refresh; reuse detection with revocation.
- `Idempotency-Key` support on outbound messaging endpoints.

## Provider Security
- Webhook signatures verified for Meta, Telegram, Eitaa, Rubika.
- Outbound messages re-check consent/suppression immediately before send.
- Provider tokens never logged; masked in audit trails.

## Infrastructure
- Backend network is internal-only (`internal: true`).
- nginx runs with `no-new-privileges:true`.
- PostgreSQL and Redis ports not exposed to host.
- Production TLS termination expected at load balancer / CDN.

## Dependencies
- Python dependencies pinned via `requirements.lock`.
- Docker images use explicit version tags.
- CI runs `pip-audit` for known vulnerabilities.