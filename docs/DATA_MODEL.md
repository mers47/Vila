# Data Model

## Core Entities

### Users & Auth
- **users** — email, password_hash (Argon2), role (admin/operator)
- **user_sessions** — JWT refresh token tracking with rotation/reuse detection

### Leads & Contacts
- **leads** — business_name, industry, city, province, website, source, score, status, temperature, tags
- **contact_points** — channel (WHATSAPP/INSTAGRAM/TELEGRAM/EITAA/RUBIKA), value, value_normalized, consent_status

### Campaigns & Outreach
- **campaigns** — name, min_score, channels, message_template, follow_up_rules
- **campaign_leads** — joins campaigns to leads with status/step tracking
- **conversations** — per lead+channel thread tracking
- **messages** — direction (inbound/outbound), status, body, idempotency_key, intent classification
- **message_attempts** — attempt ledger per message (provider, outcome, latency)

### Operations
- **outbox_events** — transactional outbox pattern (topic, aggregate_id, payload, lease recovery)
- **suppressions** — do-not-contact registry
- **audit_logs** — actor, action, entity_type, entity_id, detail
- **scoring_profiles** — configurable lead scoring weights
- **sales_handoffs** — lead → sales assignment workflow
- **discovery_jobs** — scheduled lead discovery tasks

## Key Indexes
- `ix_leads_status_score` — campaign targeting
- `ix_leads_city_industry` — discovery dedup
- `uq_contact_channel_value` — contact dedup
- `ix_outbox_due` / `ix_outbox_lease` — worker polling
- `ix_message_attempts_message_attempt` — attempt history