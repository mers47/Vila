from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import CampaignLead, Lead, Message, MessageAttempt, OutboxEvent, User
from app.services.rate_limit import circuit_delay

router = APIRouter(prefix="/ops", tags=["operations"])
CHANNELS = ("WHATSAPP", "INSTAGRAM", "TELEGRAM", "EITAA", "RUBIKA")


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin", "supervisor")),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    outbox_rows = (await db.execute(
        select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status)
    )).all()
    campaign_rows = (await db.execute(
        select(CampaignLead.status, func.count()).group_by(CampaignLead.status)
    )).all()
    attempt_rows = (await db.execute(
        select(MessageAttempt.outcome, func.count())
        .where(MessageAttempt.created_at >= since)
        .group_by(MessageAttempt.outcome)
    )).all()
    message_rows = (await db.execute(
        select(Message.status, func.count())
        .where(Message.created_at >= since)
        .group_by(Message.status)
    )).all()

    oldest_pending = await db.scalar(
        select(func.min(OutboxEvent.available_at)).where(OutboxEvent.status == "PENDING")
    )
    due_followups = await db.scalar(
        select(func.count()).select_from(Lead).where(
            Lead.next_follow_up_at.is_not(None), Lead.next_follow_up_at <= now
        )
    )
    stale_processing = await db.scalar(
        select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.status == "PROCESSING",
            OutboxEvent.locked_until.is_not(None),
            OutboxEvent.locked_until < now,
        )
    )
    circuits = await asyncio.gather(*(circuit_delay(channel) for channel in CHANNELS))

    lag_seconds = None
    if oldest_pending:
        lag_seconds = max(0, int((now - oldest_pending).total_seconds()))

    return {
        "generated_at": now,
        "outbox": {status: count for status, count in outbox_rows},
        "outbox_oldest_pending_lag_seconds": lag_seconds,
        "stale_processing_events": stale_processing or 0,
        "campaign_leads": {status: count for status, count in campaign_rows},
        "message_attempts_24h": {status: count for status, count in attempt_rows},
        "messages_24h": {status: count for status, count in message_rows},
        "due_human_followups": due_followups or 0,
        "provider_circuit_open_seconds": dict(zip(CHANNELS, circuits, strict=True)),
    }
