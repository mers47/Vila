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
from app.models.entities import (
    Campaign,
    CampaignLead,
    ContactPoint,
    Conversation,
    Lead,
    Message,
    MessageAttempt,
    OutboxEvent,
    Suppression,
)
from app.models.enums import MessageDirection, MessageStatus
from app.services.policy import can_send
from app.services.rate_limit import (
    circuit_delay,
    provider_budget,
    record_provider_failure,
    record_provider_success,
)

CONNECTORS = {
    "WHATSAPP": WhatsAppConnector,
    "INSTAGRAM": InstagramConnector,
    "TELEGRAM": TelegramConnector,
    "EITAA": EitaaConnector,
    "RUBIKA": RubikaConnector,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _conversation_id(db: AsyncSession, lead_id: UUID, channel: str) -> UUID:
    stmt = (
        pg_insert(Conversation)
        .values(id=uuid.uuid4(), lead_id=lead_id, channel=channel, human_takeover=False, created_at=_utcnow())
        .on_conflict_do_nothing(index_elements=["lead_id", "channel"])
        .returning(Conversation.id)
    )
    created_id = await db.scalar(stmt)
    if created_id:
        return created_id
    existing = await db.scalar(select(Conversation.id).where(
        Conversation.lead_id == lead_id,
        Conversation.channel == channel,
    ))
    if not existing:
        raise RuntimeError("conversation upsert failed")
    return existing


async def queue_outbound(
    db: AsyncSession,
    *,
    lead_id: UUID,
    contact_id: UUID,
    text: str,
    campaign_id: UUID | None = None,
    campaign_lead_id: UUID | None = None,
    message_kind: str = "text",
    template_name: str | None = None,
    template_language: str = "fa",
    template_components: list | None = None,
    idempotency_key: str | None = None,
) -> Message:
    if idempotency_key:
        existing = await db.scalar(select(Message).where(Message.idempotency_key == idempotency_key))
        if existing:
            return existing

    lead = await db.get(Lead, lead_id)
    contact = await db.get(ContactPoint, contact_id)
    if not lead or not contact or contact.lead_id != lead_id:
        raise ValueError("lead/contact not found")

    suppressed = await db.scalar(select(Suppression.id).where(
        Suppression.channel == contact.channel,
        Suppression.value_normalized == contact.value_normalized,
    ))
    eligibility = can_send(
        contact.channel,
        contact.consent_status,
        message_kind=message_kind,
        interaction_started=contact.interaction_started,
        last_inbound_at=contact.last_inbound_at,
    )
    conversation_id = await _conversation_id(db, lead.id, contact.channel)
    conversation = await db.get(Conversation, conversation_id)

    rendered_body = text if message_kind == "text" else f"[template:{template_name}]"
    message = Message(
        conversation_id=conversation_id,
        campaign_id=campaign_id,
        direction=MessageDirection.OUTBOUND.value,
        body=rendered_body,
        status=MessageStatus.QUEUED.value,
        idempotency_key=idempotency_key,
    )
    try:
        async with db.begin_nested():
            db.add(message)
            await db.flush()
    except IntegrityError:
        if idempotency_key:
            existing = await db.scalar(select(Message).where(Message.idempotency_key == idempotency_key))
            if existing:
                return existing
        raise

    if suppressed or not eligibility.allowed or (conversation and conversation.human_takeover and campaign_id is not None):
        message.status = MessageStatus.BLOCKED_POLICY.value
        if suppressed:
            message.error_detail = "suppressed"
        elif conversation and conversation.human_takeover and campaign_id is not None:
            message.error_detail = "human takeover active"
        else:
            message.error_detail = eligibility.reason
        return message

    if contact.channel not in CONNECTORS:
        message.status = MessageStatus.FAILED.value
        message.error_code = "UNSUPPORTED_CHANNEL"
        return message

    db.add(OutboxEvent(
        topic="SEND_MESSAGE",
        aggregate_id=str(message.id),
        payload={
            "contact_id": str(contact.id),
            "message_kind": message_kind,
            "template_name": template_name,
            "template_language": template_language,
            "template_components": template_components,
            "campaign_lead_id": str(campaign_lead_id) if campaign_lead_id else None,
        },
        status="PENDING",
        available_at=_utcnow(),
    ))
    return message


def _jitter_backoff(attempt: int, *, base: int = 5, cap: int = 3600) -> int:
    ceiling = min(cap, base * (2 ** max(0, min(attempt, 10))))
    return max(1, int(random.uniform(base, max(base, ceiling))))


async def claim_outbox(db: AsyncSession, *, limit: int | None = None) -> list[tuple[UUID, str]]:
    s = get_settings()
    now = _utcnow()
    limit = limit or s.outbox_batch_size
    rows = list((await db.scalars(
        select(OutboxEvent)
        .where(
            OutboxEvent.topic == "SEND_MESSAGE",
            OutboxEvent.available_at <= now,
            or_(
                OutboxEvent.status == "PENDING",
                (OutboxEvent.status == "PROCESSING") & (OutboxEvent.locked_until.is_not(None)) & (OutboxEvent.locked_until < now),
            ),
        )
        .order_by(OutboxEvent.available_at.asc(), OutboxEvent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )).all())
    claimed: list[tuple[UUID, str]] = []
    for event in rows:
        lease = uuid.uuid4().hex
        event.status = "PROCESSING"
        event.lease_token = lease
        event.locked_until = now + timedelta(seconds=s.outbox_lease_seconds)
        claimed.append((event.id, lease))
    await db.commit()
    return claimed


async def _defer_event(db: AsyncSession, event: OutboxEvent, seconds: int, reason: str, *, count_attempt: bool = False) -> None:
    if count_attempt:
        event.attempts += 1
    event.status = "PENDING"
    event.available_at = _utcnow() + timedelta(seconds=max(1, seconds))
    event.locked_until = None
    event.lease_token = None
    event.last_error = reason[:2000]
    await db.commit()


async def _cancel_event(db: AsyncSession, event: OutboxEvent, message: Message, reason: str, *, status: str = MessageStatus.BLOCKED_POLICY.value) -> dict:
    event.status = "CANCELLED"
    event.locked_until = None
    event.lease_token = None
    event.last_error = reason[:2000]
    message.status = status
    message.error_detail = reason[:2000]
    await db.commit()
    return {"status": event.status, "message_id": str(message.id), "reason": reason}


async def _advance_campaign(db: AsyncSession, campaign_lead_id: str | None, message: Message) -> None:
    if not campaign_lead_id:
        return
    try:
        row_id = UUID(campaign_lead_id)
    except (ValueError, TypeError):
        return
    row = await db.get(CampaignLead, row_id)
    if not row:
        return
    row.last_message_id = message.id
    row.attempts = 0
    row.last_error = None
    row.step += 1
    campaign = await db.get(Campaign, row.campaign_id)
    rules = (campaign.follow_up_rules or {}).get("steps", []) if campaign else []
    just_sent_step = row.step - 1
    if just_sent_step >= len(rules):
        row.status = "DORMANT"
        row.next_action_at = None
        return
    delay = int(rules[just_sent_step].get("after_hours", 72))
    row.status = "ACTIVE"
    row.next_action_at = _utcnow() + timedelta(hours=max(1, delay))


async def deliver_outbox_event(db: AsyncSession, event_id: UUID, lease_token: str) -> dict:
    s = get_settings()
    event = await db.scalar(select(OutboxEvent).where(
        OutboxEvent.id == event_id,
        OutboxEvent.status == "PROCESSING",
        OutboxEvent.lease_token == lease_token,
    ))
    if not event:
        return {"status": "STALE_LEASE", "event_id": str(event_id)}

    try:
        message_id = UUID(event.aggregate_id)
        contact_id = UUID(str(event.payload["contact_id"]))
    except (ValueError, TypeError, KeyError):
        event.status = "FAILED"
        event.last_error = "invalid outbox payload"
        await db.commit()
        return {"status": "FAILED", "event_id": str(event.id)}

    message = await db.get(Message, message_id)
    contact = await db.get(ContactPoint, contact_id)
    if not message or not contact:
        event.status = "FAILED"
        event.last_error = "message/contact missing"
        await db.commit()
        return {"status": "FAILED", "event_id": str(event.id)}

    conversation = await db.get(Conversation, message.conversation_id)
    lead = await db.get(Lead, contact.lead_id)
    campaign_lead_id = event.payload.get("campaign_lead_id")
    if campaign_lead_id:
        try:
            campaign_lead_uuid = UUID(str(campaign_lead_id))
        except (TypeError, ValueError):
            return await _cancel_event(db, event, message, "invalid campaign lead reference", status=MessageStatus.FAILED.value)
        row = await db.get(CampaignLead, campaign_lead_uuid)
        if not row or row.status != "WAITING_SEND":
            return await _cancel_event(db, event, message, "campaign state changed before delivery", status=MessageStatus.CANCELLED.value)
        campaign = await db.get(Campaign, row.campaign_id)
        if not campaign:
            return await _cancel_event(db, event, message, "campaign missing before delivery", status=MessageStatus.CANCELLED.value)
        if campaign.status == "PAUSED":
            await _defer_event(db, event, 60, "campaign paused")
            return {"status": "DEFERRED_PAUSED", "retry_after": 60, "message_id": str(message.id)}
        if campaign.status != "ACTIVE":
            return await _cancel_event(db, event, message, f"campaign is {campaign.status}", status=MessageStatus.CANCELLED.value)

    # TOCTOU protection: re-check current suppression, consent/session window and human takeover at delivery time.
    suppressed = await db.scalar(select(Suppression.id).where(
        Suppression.channel == contact.channel,
        Suppression.value_normalized == contact.value_normalized,
    ))
    message_kind = str(event.payload.get("message_kind") or "text")
    eligibility = can_send(
        contact.channel,
        contact.consent_status,
        message_kind=message_kind,
        interaction_started=contact.interaction_started,
        last_inbound_at=contact.last_inbound_at,
    )
    if suppressed or not eligibility.allowed or (conversation and conversation.human_takeover and message.campaign_id is not None):
        reason = "suppressed" if suppressed else ("human takeover active" if conversation and conversation.human_takeover else eligibility.reason)
        return await _cancel_event(db, event, message, reason)

    open_for = await circuit_delay(contact.channel)
    if open_for:
        await _defer_event(db, event, open_for, "provider circuit open")
        return {"status": "DEFERRED_CIRCUIT", "retry_after": open_for, "message_id": str(message.id)}

    budget = await provider_budget(contact.channel)
    if not budget.allowed:
        delay = max(1, budget.retry_after_seconds)
        await _defer_event(db, event, delay, "local token bucket backpressure")
        return {"status": "DEFERRED_RATE", "retry_after": delay, "message_id": str(message.id)}

    connector_cls = CONNECTORS.get(contact.channel)
    if not connector_cls:
        return await _cancel_event(db, event, message, "unsupported channel", status=MessageStatus.FAILED.value)
    connector = connector_cls()

    try:
        if contact.channel == "WHATSAPP" and message_kind in {"template", "marketing_template"}:
            template_name = event.payload.get("template_name")
            if not template_name:
                return await _cancel_event(db, event, message, "template_name required", status=MessageStatus.FAILED.value)
            sender = connector.send_marketing_template if message_kind == "marketing_template" else connector.send_template
            result = await sender(
                contact.value,
                name=str(template_name),
                language=str(event.payload.get("template_language") or "fa"),
                components=event.payload.get("template_components"),
            )
        else:
            result = await connector.send_text(contact.value, message.body)
    except Exception as exc:
        attempt_no = event.attempts + 1
        db.add(MessageAttempt(
            message_id=message.id,
            attempt_no=attempt_no,
            provider=contact.channel,
            outcome="EXCEPTION",
            error_code=exc.__class__.__name__,
            error_detail=str(exc)[:2000],
        ))
        event.attempts = attempt_no
        delay = _jitter_backoff(attempt_no)
        message.status = MessageStatus.RETRYING.value
        message.error_code = exc.__class__.__name__
        message.error_detail = str(exc)[:2000]
        if attempt_no >= s.outbox_max_attempts:
            event.status = "FAILED"; event.locked_until = None; event.lease_token = None
            message.status = MessageStatus.FAILED.value
        else:
            event.status = "PENDING"; event.available_at = _utcnow() + timedelta(seconds=delay)
            event.locked_until = None; event.lease_token = None
        event.last_error = str(exc)[:2000]
        await record_provider_failure(contact.channel)
        await db.commit()
        return {"status": event.status, "retry_after": delay if event.status == "PENDING" else None, "message_id": str(message.id)}

    attempt_no = event.attempts + 1
    db.add(MessageAttempt(
        message_id=message.id,
        attempt_no=attempt_no,
        provider=contact.channel,
        outcome="SENT" if result.success else "FAILED",
        http_status=result.http_status,
        error_code=result.error_code,
        error_detail=(result.error_detail or "")[:2000] or None,
        retry_after_seconds=result.retry_after_seconds,
        latency_ms=result.latency_ms,
    ))
    event.attempts = attempt_no

    if result.success:
        now = _utcnow()
        message.status = MessageStatus.SENT.value
        message.external_message_id = result.external_message_id
        message.error_code = None
        message.error_detail = None
        message.sent_at = now
        event.status = "DONE"
        event.locked_until = None
        event.lease_token = None
        event.last_error = None
        if lead:
            lead.status = "CONTACTED"
            lead.last_contact_at = now
        await _advance_campaign(db, campaign_lead_id, message)
        await record_provider_success(contact.channel)
        await db.commit()
        return {"status": "DONE", "message_id": str(message.id), "external_message_id": result.external_message_id}

    message.error_code = result.error_code
    message.error_detail = (result.error_detail or "")[:2000] or None
    event.last_error = message.error_detail or message.error_code
    if result.retryable and attempt_no < s.outbox_max_attempts:
        delay = result.retry_after_seconds or _jitter_backoff(attempt_no)
        message.status = MessageStatus.RETRYING.value
        event.status = "PENDING"
        event.available_at = _utcnow() + timedelta(seconds=delay)
        event.locked_until = None
        event.lease_token = None
        await record_provider_failure(contact.channel)
        await db.commit()
        return {"status": "PENDING", "retry_after": delay, "message_id": str(message.id)}

    message.status = MessageStatus.FAILED.value
    event.status = "FAILED"
    event.locked_until = None
    event.lease_token = None
    if campaign_lead_id:
        try:
            failed_row_id = UUID(str(campaign_lead_id))
        except (TypeError, ValueError):
            failed_row_id = None
        row = await db.get(CampaignLead, failed_row_id) if failed_row_id else None
        if row:
            row.status = "ERROR"
            row.last_error = event.last_error
            row.next_action_at = None
    await db.commit()
    return {"status": "FAILED", "message_id": str(message.id), "error_code": result.error_code}


async def send_outbound(db: AsyncSession, **kwargs) -> Message:
    return await queue_outbound(db, **kwargs)
