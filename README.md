# Lead Platform V2 — Enterprise Hardened

پلتفرم فارسی مشتری‌یابی و CRM برای **Discovery → Qualification → compliant outreach → inbound classification → follow-up → sales handoff**.

## Tech Stack
- **Backend:** FastAPI (Python 3.13) + SQLAlchemy async + Celery + PostgreSQL 18.4 + Redis 8.6
- **Frontend:** Next.js 16.3 + TypeScript
- **Infra:** Docker Compose + nginx reverse proxy

## Quick Start
```bash
cp .env.example .env
docker compose up -d --build
make admin ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='A-Strong-Password-Here'
```

## Features
- Multi-provider Outreach: WhatsApp, Instagram, Telegram, Eitaa, Rubika
- Lead Discovery: Google Places, Instagram Graph API, Public Web
- Enterprise Hardening: Transactional Outbox, Circuit Breaker, Rate Limiting, Session Rotation
- Persian-first: Scoring, Classification, Templates all Persian-optimized

## Documentation
- `docs/ELITE_AUDIT.md` — Architecture audit & known risks
- `docs/PRODUCTION.md` — Deployment runbook
- `docs/CONNECTORS.md` — Provider connectors
- `docs/DATA_MODEL.md` — Database schema