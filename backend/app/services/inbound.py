from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import CampaignLead, ContactPoint, Conversation, Lead, Message, Suppression
from app.models.enums import ConsentStatus, MessageDirection, MessageStatus
from app.services.reply_classifier import classify_reply


async def process_inbound_message(
    db: AsyncSession,
    *,
    channel: str,
    sender_id: str,
    text: str,
    external_message_id: str | None = None,
) -> Message | None:
    norm_value = sender_id.strip().lower()

    contact = await db.scalar(
        select(ContactPoint).where(
            ContactPoint.channel == channel,
            ContactPoint.value_normalized == norm_value,
        )
    )
    if not contact:
        return None

    contact.interaction_started = True
    contact.last_inbound_at = Message.__dict__  # simplified

    if contact.consent_status == ConsentStatus.UNKNOWN.value:
        contact.consent_status = ConsentStatus.IMPLIED.value

    lead = await db.get(Lead, contact.lead_id)
    if not lead:
        return None

    intent_label, confidence = classify_reply(text)

    msg = Message(
        conversation_id=await _ensure_conversation(db, lead.id, channel),
        direction=MessageDirection.INBOUND.value,
        status=MessageStatus.DELIVERED.value,
        body=text,
        external_message_id=external_message_id,
        intent_label=intent_label,
        intent_confidence=confidence,
        classification_engine="rules-v2",
    )
    db.add(msg)

    if intent_label == "OPTOUT" and confidence >= 70:
        contact.consent_status = ConsentStatus.OPTED_OUT.value
        db.add(Suppression(channel=channel, value_normalized=norm_value, reason="user_optout"))

    await db.flush()
    return msg


async def _ensure_conversation(db: AsyncSession, lead_id: UUID, channel: str) -> UUID:
    existing = await db.scalar(select(Conversation.id).where(Conversation.lead_id == lead_id, Conversation.channel == channel))
    if existing:
        return existing
    conv = Conversation(lead_id=lead_id, channel=channel)
    db.add(conv)
    await db.flush()
    return conv.id