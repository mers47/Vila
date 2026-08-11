from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Campaign, CampaignLead, ContactPoint, Lead


async def enroll_lead(db: AsyncSession, lead_id: UUID, campaign_id: UUID) -> CampaignLead | None:
    campaign = await db.get(Campaign, campaign_id)
    lead = await db.get(Lead, lead_id)
    if not campaign or not lead:
        return None
    if lead.score < campaign.min_score:
        return None

    contacts = (await db.execute(select(ContactPoint).where(ContactPoint.lead_id == lead_id))).scalars().all()
    valid_channels = set(campaign.channels or [])
    contact = next((c for c in contacts if c.channel in valid_channels and c.is_valid), None)
    if not contact:
        return None

    cl = CampaignLead(campaign_id=campaign_id, lead_id=lead_id, contact_id=contact.id, status="ACTIVE", step=0)
    db.add(cl)
    await db.flush()
    return cl


async def get_campaign_queue(db: AsyncSession, campaign_id: UUID, limit: int = 50) -> list[CampaignLead]:
    return list((await db.execute(
        select(CampaignLead).where(
            CampaignLead.campaign_id == campaign_id,
            CampaignLead.status.in_(["ACTIVE", "RETRYING"]),
        ).order_by(CampaignLead.next_action_at.asc().nullsfirst()).limit(limit)
    )).scalars().all())


async def advance_campaign_lead(db: AsyncSession, campaign_lead_id: UUID, error: str | None = None):
    cl = await db.get(CampaignLead, campaign_lead_id)
    if not cl:
        return
    if error:
        cl.attempts += 1
        if cl.attempts >= 5:
            cl.status = "FAILED"
        else:
            cl.status = "RETRYING"
        cl.last_error = error
    else:
        cl.step += 1
        cl.status = "ACTIVE"
    await db.flush()