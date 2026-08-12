from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import ContactPoint, Conversation, Message, Lead, Suppression, SalesHandoff, CampaignLead
from app.models.enums import MessageDirection, MessageStatus
from app.services.normalization import normalize_contact
from app.services.reply_classifier import classify_reply, classify_reply_detailed
from app.services.audit import audit


async def record_inbound(
    db: AsyncSession,
    *,
    channel: str,
    sender: str,
    body: str,
    external_message_id: str | None = None,
    display_name: str | None = None,
) -> dict:
    channel = channel.upper()
    if external_message_id:
        duplicate = await db.execute(
            select(Message, Conversation).join(Conversation, Message.conversation_id == Conversation.id).where(
                Message.external_message_id == external_message_id,
                Message.direction == MessageDirection.INBOUND.value,
                Conversation.channel == channel,
            )
        )
        found = duplicate.first()
        if found:
            msg, conv = found
            existing_lead = await db.get(Lead, conv.lead_id)
            return {"matched": True, "duplicate": True, "lead_id": str(conv.lead_id),
                    "intent": classify_reply(msg.body), "status": existing_lead.status if existing_lead else None}
    normalized = normalize_contact(channel, sender)
    contact = await db.scalar(select(ContactPoint).where(
        ContactPoint.channel == channel,
        ContactPoint.value_normalized == normalized,
    ))
    now = datetime.now(timezone.utc)
    if not contact:
        lead = Lead(
            business_name=(display_name or f"{channel} inbound")[:255],
            source=f"{channel}_INBOUND",
            status="REPLIED",
            temperature="WARM",
            metadata_json={"created_from_inbound": True},
        )
        db.add(lead)
        await db.flush()
        contact = ContactPoint(
            lead_id=lead.id,
            channel=channel,
            value=sender,
            value_normalized=normalized,
            interaction_started=True,
            last_inbound_at=now,
        )
        db.add(contact)
        await db.flush()
    else:
        lead = await db.get(Lead, contact.lead_id)
        contact.interaction_started = True
        contact.last_inbound_at = now

    conversation = await db.scalar(select(Conversation).where(
        Conversation.lead_id == lead.id,
        Conversation.channel == channel,
    ))
    if not conversation:
        conversation = Conversation(lead_id=lead.id, channel=channel)
        db.add(conversation)
        await db.flush()

    message = Message(
        conversation_id=conversation.id,
        direction=MessageDirection.INBOUND.value,
        status=MessageStatus.DELIVERED.value,
        body=body,
        external_message_id=external_message_id,
        delivered_at=now,
    )
    try:
        async with db.begin_nested():
            db.add(message)
            await db.flush()
    except IntegrityError:
        existing = await db.scalar(select(Message).where(
            Message.conversation_id == conversation.id,
            Message.direction == MessageDirection.INBOUND.value,
            Message.external_message_id == external_message_id,
        ))
        await db.commit()
        return {"matched": True, "duplicate": True, "lead_id": str(lead.id),
                "intent": classify_reply(existing.body if existing else body), "status": lead.status}
    classification = classify_reply_detailed(body)
    intent = classification.label
    message.intent_label = classification.label
    message.intent_confidence = round(classification.confidence * 100)
    message.classification_engine = classification.engine
    lead.last_contact_at = now
    lead.status = "REPLIED"

    active_campaign_rows = list((await db.scalars(select(CampaignLead).where(
        CampaignLead.lead_id == lead.id, CampaignLead.status.in_(["ACTIVE", "PAUSED", "WAITING_SEND"])
    ))).all())
    for campaign_row in active_campaign_rows:
        campaign_row.status = "REPLIED"
        campaign_row.next_action_at = None

    if intent == "PURCHASE_INTENT":
        lead.status = "HOT"
        lead.temperature = "HOT"
        conversation.human_takeover = True
        existing_handoff = await db.scalar(select(SalesHandoff).where(
            SalesHandoff.lead_id == lead.id, SalesHandoff.status.in_(["NEW", "CLAIMED"])
        ))
        if not existing_handoff:
            handoff = SalesHandoff(lead_id=lead.id, reason="PURCHASE_INTENT")
            db.add(handoff)
            await db.flush()
            await audit(db, action="sales_handoff.created", entity_type="sales_handoff", entity_id=str(handoff.id),
                        actor_user_id=None, detail={"lead_id": str(lead.id), "reason": "PURCHASE_INTENT"})
        for campaign_row in active_campaign_rows:
            campaign_row.status = "HANDED_TO_SALES"
    elif intent == "FOLLOW_UP_LATER":
        lead.status = "FOLLOW_UP"
        lead.next_follow_up_at = now + timedelta(days=7)
    elif intent == "NOT_INTERESTED":
        lead.status = "NOT_INTERESTED"
        for campaign_row in active_campaign_rows:
            campaign_row.status = "NOT_INTERESTED"
    elif intent == "OPT_OUT":
        lead.status = "DO_NOT_CONTACT"
        contact.consent_status = "OPTED_OUT"
        existing = await db.scalar(select(Suppression).where(
            Suppression.channel == contact.channel,
            Suppression.value_normalized == contact.value_normalized,
        ))
        if not existing:
            db.add(Suppression(channel=contact.channel, value_normalized=contact.value_normalized, reason="recipient opt-out"))
        for campaign_row in active_campaign_rows:
            campaign_row.status = "OPTED_OUT"
        await audit(db, action="contact.opted_out", entity_type="contact_point", entity_id=str(contact.id),
                    actor_user_id=None, detail={"lead_id": str(lead.id), "channel": channel})

    await db.commit()
    return {"matched": True, "lead_id": str(lead.id), "intent": intent, "status": lead.status}
