# Delivery Notes

## What's Included
- Full source code (backend + frontend)
- Docker Compose production configuration
- Database migrations (Alembic)
- 23 unit/integration tests
- Comprehensive documentation

## What's NOT Included
- Provider API credentials (you must obtain your own)
- TLS certificates (use your own load balancer / CDN)
- CI/CD pipeline beyond the included GitHub Actions workflow
- Monitoring/alerting infrastructure

## Provider Setup Required
1. **Meta (WhatsApp + Instagram)**: Create a Meta Business App, configure Webhook, get access tokens
2. **Telegram**: Create a bot via @BotFather, set webhook
3. **Eitaa**: Obtain app token from Eitaa panel
4. **Rubika**: Create bot, get token and webhook secret
5. **Google Places**: Enable Places API, create API key

## Deployment Steps
1. Clone repository
2. Copy `.env.example` to `.env` and fill in all values
3. Run `docker compose up -d --build`
4. Create admin user: `make admin ADMIN_EMAIL=... ADMIN_PASSWORD=...`
5. Configure provider webhooks (see docs/CONNECTORS.md)