# Production Deployment Runbook

## Prerequisites
- Docker Engine 24+ with Compose v2
- PostgreSQL 18.4 (or use included container)
- Redis 8.6 (or use included container)
- Domain with TLS (terminate at load balancer)

## Environment Variables (Required)
| Variable | Description |
|---|---|
| `SECRET_KEY` | >= 32 random chars for JWT signing |
| `POSTGRES_PASSWORD` | Strong database password |
| `FRONTEND_ORIGIN` | Your dashboard URL (e.g. `https://crm.example.com`) |
| `ENVIRONMENT` | Set to `production` |
| `COOKIE_SECURE` | Set to `true` for HTTPS |

## Provider Credentials
See `docs/CONNECTORS.md` for provider-specific setup.

## Startup
```bash
git clone <repo> && cd lead-platform-enterprise-v2
cp .env.example .env
# Edit .env with production values
docker compose up -d --build
make admin ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='...'
curl http://localhost:8080/health
```

## Scaling
- **API**: `docker compose up -d --scale api=3` (requires load balancer)
- **Workers**: Adjust `--concurrency` per worker in docker-compose.yml
- **Database**: Consider managed PostgreSQL with read replicas for > 1M leads

## Backups
```bash
./scripts/backup_postgres.sh
./scripts/restore_postgres.sh <backup-file>
```

## Monitoring
- `/metrics` endpoint exposes Prometheus metrics
- `/ops` dashboard shows outbox lag, circuit breaker state

## Troubleshooting
| Symptom | Check |
|---|---|
| API not responding | `docker compose ps`, `docker compose logs api` |
| Messages stuck queued | `docker compose logs worker-outbound`, check provider credentials |
| Discovery not running | `docker compose logs worker-discovery`, check `discovery_jobs` table |
| Login failures | Check `auth_login_attempts_per_15m` rate limit, verify `SECRET_KEY` |