from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Lead, ContactPoint
from app.schemas.leads import LeadCreate
from app.services.audit import audit
from app.services.normalization import normalize_contact


async def upsert_lead(
    db: AsyncSession,
    payload: LeadCreate,
    *,
    actor_user_id: UUID | None = None,
) -> tuple[Lead, bool]:
    """Create a lead or merge onto an existing lead identified by provider ID/contact.

    Does not commit; callers own the transaction so bulk discovery/import remains atomic and efficient.
    """
    existing: Lead | None = None
    if payload.source_external_id:
        existing = await db.scalar(select(Lead).where(
            Lead.source == payload.source,
            Lead.source_external_id == payload.source_external_id,
        ))

    normalized_contacts = [(c, normalize_contact(c.channel, c.value)) for c in payload.contacts if c.value.strip()]
    if existing is None:
        for contact, norm in normalized_contacts:
            cp = await db.scalar(select(ContactPoint).where(
                ContactPoint.channel == contact.channel.upper(),
                ContactPoint.value_normalized == norm,
            ))
            if cp:
                existing = await db.get(Lead, cp.lead_id)
                if existing:
                    break

    if existing:
        # Enrich missing fields without overwriting known operator-curated data.
        for attr in ("industry", "province", "city", "address", "website"):
            if not getattr(existing, attr) and getattr(payload, attr):
                setattr(existing, attr, getattr(payload, attr))
        if payload.tags:
            existing.tags = sorted(set((existing.tags or []) + payload.tags))
        if payload.metadata_json:
            existing.metadata_json = {**(existing.metadata_json or {}), **payload.metadata_json}
        existing_contact_keys = set((await db.execute(
            select(ContactPoint.channel, ContactPoint.value_normalized).where(ContactPoint.lead_id == existing.id)
        )).all())
        for contact, norm in normalized_contacts:
            key = (contact.channel.upper(), norm)
            if key not in existing_contact_keys:
                globally_used = await db.scalar(select(ContactPoint.id).where(
                    ContactPoint.channel == key[0], ContactPoint.value_normalized == key[1]
                ))
                if not globally_used:
                    db.add(ContactPoint(
                        lead_id=existing.id, channel=key[0], value=contact.value,
                        value_normalized=norm, consent_status=contact.consent_status.upper(),
                        consent_source=contact.consent_source,
                    ))
        return existing, False

    lead = Lead(
        business_name=payload.business_name,
        industry=payload.industry,
        province=payload.province,
        city=payload.city,
        address=payload.address,
        website=payload.website,
        source=payload.source,
        source_external_id=payload.source_external_id,
        tags=payload.tags,
        metadata_json=payload.metadata_json,
    )
    db.add(lead)
    await db.flush()
    for contact, norm in normalized_contacts:
        db.add(ContactPoint(
            lead_id=lead.id,
            channel=contact.channel.upper(),
            value=contact.value,
            value_normalized=norm,
            consent_status=contact.consent_status.upper(),
            consent_source=contact.consent_source,
        ))
    await audit(db, action="lead.created", entity_type="lead", entity_id=str(lead.id),
                actor_user_id=actor_user_id, detail={"source": payload.source})
    return lead, True
