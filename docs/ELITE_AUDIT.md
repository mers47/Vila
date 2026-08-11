# Elite Audit Report — Lead Platform V2

## Overview
This document catalogs known weaknesses, mitigations applied in V2, and remaining risks.

## V1 Weaknesses → V2 Mitigations

### 1. Redis as Message Bus
**V1 Problem:** Redis used as primary message broker — no durability guarantee, at-least-once semantics.
**V2 Fix:** Transactional PostgreSQL Outbox (`outbox_events`). Messages written in same DB transaction as business data. Redis only used for Celery transport and caching.
**Risk Remaining:** Outbox poller latency (mitigated by `available_at` scheduling and `SKIP LOCKED`).

### 2. No Idempotency
**V1 Problem:** Duplicate outbound messages possible on retry.
**V2 Fix:** `idempotency_key` on messages table with unique constraint. Queue checks before insert.
**Risk Remaining:** Provider-side duplicates if response lost after send (mitigated by attempt tracking).

### 3. No Rate Limiting
**V1 Problem:** No backpressure — could flood providers.
**V2 Fix:** Token-bucket rate limiter per provider, configurable `outbound_requests_per_second`. Circuit breaker opens after `provider_circuit_failures` consecutive failures.
**Risk Remaining:** Burst allowance tuning needed per provider.

### 4. Session Vulnerabilities
**V1 Problem:** Long-lived tokens, no rotation.
**V2 Fix:** Refresh token rotation, reuse detection, session revocation, cookie CSRF guard.
**Risk Remaining:** Token stored in httpOnly cookie — XSS risk if frontend compromised (mitigated by strict CSP).

### 5. Consent Gaps
**V1 Problem:** Consent checked only at campaign enrollment.
**V2 Fix:** Re-check consent + suppression right before each send in `can_send()`.
**Risk Remaining:** Async gap between check and send (sub-second window, acceptable).

### 6. No Operations Visibility
**V1 Problem:** Black box when messages fail.
**V2 Fix:** `message_attempts` ledger, `/ops` dashboard, Prometheus metrics (`lead_platform_http_requests_total`, etc.).
**Risk Remaining:** No distributed tracing (acceptable for v2 scope).

### 7. AI/ML Claims Without Substance
**V1 Problem:** "AI-powered scoring", "smart classification" — marketing terms.
**V2 Fix:** Explainable rules-based scoring (`ScoringProfile` weights), deterministic `reply_classifier` with confidence scores, no black-box AI.
**Risk Remaining:** Classifier accuracy limited to rule coverage (honest about this).

## Known Risks (Accepted)
- **Single PostgreSQL instance** — no read replicas or failover. Acceptable for < 1M leads.
- **No horizontal API scaling** — single API container. Compose scale-out documented in PRODUCTION.md.
- **No secrets manager** — secrets in .env file. Acceptable for single-server deployment.
- **Provider API changes** — connectors may break on API version bumps. Version pinning helps.

## Architecture Verdict
**Production-ready for single-server deployment with < 1M leads.** Requires multi-node architecture for larger scale. Honest about limitations — no fake AI claims, no hidden gotchas.