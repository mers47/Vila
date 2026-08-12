from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Campaign, CampaignLead, ContactPoint, Lead, Suppression
from app.models.enums import MessageStatus
from app.services.outreach import queue_outbound
from app.services.policy import can_send
from app.services.templates import render_message


def _message_spec(campaign: Campaign, contact: ContactPoint, step: int, lead: Lead) -> dict:
    if step == 0:
        if contact.channel == "WHATSAPP":
            cfg = (campaign.provider_templates or {}).get("WHATSAPP") or {}
            if cfg.get("name"):
                return {
                    "message_kind": cfg.get("kind", "marketing_template"),
                    "template_name": cfg["name"],
                    "template_language": cfg.get("language", "fa"),
                    "template_components": cfg.get("components"),
                    "text": "",
                }
        return {"message_kind": "text", "text": render_message(campaign.message_template, lead.__dict__)}

    rules = (campaign.follow_up_rules or {}).get("steps", [])
    idx = step - 1
    if idx >= len(rules):
        return {"done": True}
    rule = rules[idx]
    if contact.channel == "WHATSAPP" and rule.get("template_name"):
        return {
            "message_kind": str(rule.get("template_kind", "marketing_template")),
            "template_name": str(rule["template_name"]),
            "template_language": str(rule.get("template_language", "fa")),
            "template_components": rule.get("template_components"),
            "text": "",
        }
    return {
        "message_kind": "text",
        "text": render_message(str(rule.get("text", "")), lead.__dict__),
    }


async def enroll_campaign(db: AsyncSession, campaign: Campaign, limit: int = 5000) -> dict:
    # Avoid the old N+1 pattern: leads+contacts, existing enrollments and suppressions are
    # fetched in bounded set-based queries before the in-memory eligibility pass.
    leads = list((await db.scalars(
        select(Lead)
        .options(selectinload(Lead.contacts))
        .where(Lead.score >= campaign.min_score, Lead.status.not_in(["DO_NOT_CONTACT", "NOT_INTERESTED"]))
        .order_by(Lead.score.desc(), Lead.created_at.desc())
        .limit(limit)
    )).all())
    existing_ids = set((await db.scalars(
        select(CampaignLead.lead_id).where(CampaignLead.campaign_id == campaign.id)
    )).all())
    suppressions = set((await db.execute(
        select(Suppression.channel, Suppression.value_normalized).where(Suppression.channel.in_(campaign.channels))
    )).all())

    channel_rank = {channel: idx for idx, channel in enumerate(campaign.channels)}
    enrolled = blocked = already = 0
    now = datetime.now(timezone.utc)
    for lead in leads:
        if lead.id in existing_ids:
            already += 1
            continue
        contacts = sorted(
            (c for c in lead.contacts if c.is_valid and c.channel in channel_rank),
            key=lambda c: channel_rank.get(c.channel, 999),
        )
        chosen = None
        for contact in contacts:
            if (contact.channel, contact.value_normalized) in suppressions:
                continue
            spec = _message_spec(campaign, contact, 0, lead)
            eligible = can_send(
                contact.channel,
                contact.consent_status,
                message_kind=spec.get("message_kind", "text"),
                interaction_started=contact.interaction_started,
                last_inbound_at=contact.last_inbound_at,
            )
            if eligible.allowed:
                chosen = contact
                break
        if not chosen:
            blocked += 1
            continue
        db.add(CampaignLead(
            campaign_id=campaign.id,
            lead_id=lead.id,
            contact_id=chosen.id,
            status="ACTIVE",
            step=0,
            next_action_at=now,
        ))
        enrolled += 1
    campaign.status = "ACTIVE"
    await db.commit()
    return {"enrolled": enrolled, "blocked_or_ineligible": blocked, "already_enrolled": already}


async def process_due_campaign_leads(db: AsyncSession, limit: int = 200) -> dict:
    now = datetime.now(timezone.utc)
    rows = list((await db.scalars(
        select(CampaignLead)
        .where(
            CampaignLead.status == "ACTIVE",
            CampaignLead.next_action_at.is_not(None),
            CampaignLead.next_action_at <= now,
        )
        .order_by(CampaignLead.next_action_at.asc(), CampaignLead.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )).all())

    queued = blocked = failed = completed = 0
    for row in rows:
        campaign = await db.get(Campaign, row.campaign_id)
        lead = await db.get(Lead, row.lead_id)
        contact = await db.get(ContactPoint, row.contact_id)
        if not campaign or not lead or not contact:
            row.status = "ERROR"
            row.last_error = "missing campaign/lead/contact"
            row.next_action_at = None
            failed += 1
            continue
        if campaign.status != "ACTIVE":
            row.status = "PAUSED" if campaign.status == "PAUSED" else "ERROR"
            row.next_action_at = None
            continue

        spec = _message_spec(campaign, contact, row.step, lead)
        if spec.get("done"):
            row.status = "DORMANT"
            row.next_action_at = None
            completed += 1
            continue

        try:
            msg = await queue_outbound(
                db,
                lead_id=lead.id,
                contact_id=contact.id,
                text=spec.get("text", ""),
                campaign_id=campaign.id,
                campaign_lead_id=row.id,
                message_kind=spec.get("message_kind", "text"),
                template_name=spec.get("template_name"),
                template_language=spec.get("template_language", "fa"),
                template_components=spec.get("template_components"),
                idempotency_key=f"campaign:{row.id}:step:{row.step}",
            )
        except Exception as exc:
            row.attempts += 1
            row.last_error = str(exc)[:1000]
            failed += 1
            if row.attempts >= 5:
                row.status = "ERROR"
                row.next_action_at = None
            continue

        row.last_message_id = msg.id
        if msg.status in {MessageStatus.QUEUED.value, MessageStatus.RETRYING.value}:
            row.status = "WAITING_SEND"
            row.next_action_at = None
            row.last_error = None
            queued += 1
        elif msg.status == MessageStatus.BLOCKED_POLICY.value:
            row.status = "BLOCKED"
            row.next_action_at = None
            row.last_error = msg.error_detail
            blocked += 1
        elif msg.status == MessageStatus.SENT.value:
            row.status = "DORMANT"
            row.next_action_at = None
            completed += 1
        else:
            row.status = "ERROR"
            row.next_action_at = None
            row.last_error = msg.error_detail or msg.error_code
            failed += 1

    await db.commit()
    return {"processed": len(rows), "queued": queued, "blocked": blocked, "failed": failed, "completed": completed}
