from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.eitaa import EitaaConnector
from app.connectors.instagram import InstagramConnector
from app.connectors.rubika import RubikaConnector
from app.connectors.telegram import TelegramConnector
from app.connectors.whatsapp import WhatsAppConnector
from app.core.config import get_settings
from app.models.entities import Campaign, CampaignLead, ContactPoint, Conversation, Lead, Message, MessageAttempt, OutboxEvent, Suppression
from app.models.enums import MessageDirection, MessageStatus
from app.services.policy import can_send
from app.services.rate_limit import circuit_delay, provider_budget, record_provider_failure, record_provider_success

CONNECTORS = {"WHATSAPP": WhatsAppConnector, "INSTAGRAM": InstagramConnector, "TELEGRAM": TelegramConnector, "EITAA": EitaaConnector, "RUBIKA": RubikaConnector}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _conversation_id(db: AsyncSession, lead_id: UUID, channel: str) -> UUID:
    stmt = pg_insert(Conversation).values(id=uuid.uuid4(), lead_id=lead_id, channel=channel, human_takeover=False, created_at=_utcnow()).on_conflict_do_nothing(index_elements=["lead_id", "channel"]).returning(Conversation.id)
    created_id = await db.scalar(stmt)
    if created_id:
        return created_id
    existing = await db.scalar(select(Conversation.id).where(Conversation.lead_id == lead_id, Conversation.channel == channel))
    if not existing:
        raise RuntimeError("conversation upsert failed")
    return existing


async def queue_outbound(db: AsyncSession, *, lead_id: UUID, contact_id: UUID, text: str, campaign_id: UUID | None = None, campaign_lead_id: UUID | None = None, idempotency_key: str | None = None) -> Message:
    if idempotency_key:
        existing = await db.scalar(select(Message).where(Message.idempotency_key == idempotency_key))
        if existing:
            return existing

    lead = await db.get(Lead, lead_id)
    contact = await db.get(ContactPoint, contact_id)
    if not lead or not contact or contact.lead_id != lead_id:
        raise ValueError("lead/contact not found")

    suppressed = await db.scalar(select(Suppression.id).where(Suppression.channel == contact.channel, Suppression.value_normalized == contact.value_normalized))
    eligibility, reason = can_send(contact.channel, contact.consent_status, contact.interaction_started, suppressed is not None, contact.is_valid)
    if not eligibility:
        return Message(status=MessageStatus.REJECTED.value, body=text, direction=MessageDirection.OUTBOUND.value, error_code=reason)

    conv_id = await _conversation_id(db, lead.id, contact.channel)
    msg = Message(conversation_id=conv_id, campaign_id=campaign_id, direction=MessageDirection.OUTBOUND.value, status=MessageStatus.QUEUED.value, body=text, idempotency_key=idempotency_key)
    db.add(msg)
    await db.flush()

    if campaign_lead_id:
        cl = await db.get(CampaignLead, campaign_lead_id)
        if cl:
            cl.last_message_id = msg.id

    return msg


async def dispatch_message(db: AsyncSession, message_id: UUID):
    msg = await db.get(Message, message_id)
    if not msg:
        return

    contact = await db.scalar(select(ContactPoint).where(ContactPoint.lead_id == (await db.get(Conversation, msg.conversation_id)).lead_id, ContactPoint.channel == (await db.get(Conversation, msg.conversation_id)).channel))
    if not contact:
        msg.status = MessageStatus.FAILED.value
        return

    provider = contact.channel
    delay = await circuit_delay(provider)
    if delay > 0:
        return

    if not await provider_budget(provider):
        return

    connector_cls = CONNECTORS.get(provider)
    if not connector_cls:
        msg.status = MessageStatus.FAILED.value
        return

    connector = connector_cls()
    result = await connector.send_text(contact.value, msg.body)

    attempt = MessageAttempt(message_id=msg.id, attempt_no=1, provider=provider, outcome="SUCCESS" if result.success else "FAILURE", http_status=result.http_status, error_code=result.error_code, error_detail=result.error_detail, retry_after_seconds=result.retry_after_seconds, latency_ms=0)
    db.add(attempt)

    if result.success:
        await record_provider_success(provider)
        msg.status = MessageStatus.SENT.value
        msg.external_message_id = result.external_id
    else:
        await record_provider_failure(provider)
        msg.status = MessageStatus.FAILED.value
        msg.error_code = result.error_code
        msg.error_detail = result.error_detail

    await db.flush()