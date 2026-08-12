from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.connectors.google_places import GooglePlacesConnector
from app.connectors.public_web import PublicWebConnector
from app.models.entities import DiscoveryJob
from app.schemas.leads import LeadCreate, ContactIn
from app.services.lead_upsert import upsert_lead
from app.services.lead_scoring import apply_active_profile
from app.services.audit import audit
from app.services.web_ingest import page_to_payload


async def execute_discovery_job(db: AsyncSession, job_id: UUID) -> dict:
    job = await db.get(DiscoveryJob, job_id)
    if not job:
        raise ValueError("discovery job not found")
    job.last_error = None
    try:
        new_count = 0
        if job.source == "GOOGLE_PLACES":
            full_query = f"{job.query} {job.city}" if job.city else job.query
            items = await GooglePlacesConnector().text_search(full_query, max_results=job.max_results)
            for p in items:
                contacts=[]
                phone=p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber")
                if phone: contacts.append(ContactIn(channel="PHONE", value=phone))
                if p.get("websiteUri"): contacts.append(ContactIn(channel="WEB", value=p["websiteUri"]))
                lead, created = await upsert_lead(db, LeadCreate(
                    business_name=p.get("displayName",{}).get("text") or "Unknown business",
                    industry=p.get("primaryType"), city=job.city, address=p.get("formattedAddress"),
                    website=p.get("websiteUri"), source="GOOGLE_PLACES", source_external_id=p.get("id"),
                    contacts=contacts, metadata_json={"business_status":p.get("businessStatus"),"discovery_job_id":str(job.id)},
                ), actor_user_id=job.created_by_user_id)
                await apply_active_profile(db, lead, has_contact=bool(contacts), has_social=False)
                new_count += int(created)
            found_count=len(items); descriptor=full_query
        elif job.source == "PUBLIC_WEB":
            pages = await PublicWebConnector().crawl_site(job.query, max_pages=job.max_results)
            for page in pages:
                payload = page_to_payload(page, source="PUBLIC_WEB")
                payload.metadata_json["discovery_job_id"] = str(job.id)
                lead, created = await upsert_lead(db, payload, actor_user_id=job.created_by_user_id)
                await apply_active_profile(db, lead, has_contact=bool(page.phones or page.whatsapp),
                                           has_social=bool(page.instagram or page.telegram))
                new_count += int(created)
            found_count=len(pages); descriptor=job.query
        else:
            raise ValueError(f"unsupported discovery source: {job.source}")

        job = await db.get(DiscoveryJob, job_id)
        job.last_run_at = datetime.now(timezone.utc)
        job.last_result_count = found_count
        job.last_error = None
        await audit(db, action="discovery_job.completed", entity_type="discovery_job", entity_id=str(job.id),
                    actor_user_id=None, detail={"found":found_count,"created":new_count,"target":descriptor,"source":job.source})
        await db.commit()
        return {"job_id":str(job.id),"found":found_count,"created":new_count}
    except Exception as exc:
        await db.rollback()
        job = await db.get(DiscoveryJob, job_id)
        if job:
            job.last_run_at = datetime.now(timezone.utc)
            job.last_error = str(exc)[:2000]
            await audit(db, action="discovery_job.failed", entity_type="discovery_job", entity_id=str(job.id),
                        actor_user_id=None, detail={"error":job.last_error})
            await db.commit()
        raise


async def due_job_ids(db: AsyncSession, limit: int = 20) -> list[UUID]:
    """Atomically claim due schedules before jobs are enqueued."""
    now = datetime.now(timezone.utc)
    rows = list((await db.scalars(
        select(DiscoveryJob).where(
            DiscoveryJob.is_enabled.is_(True),
            DiscoveryJob.next_run_at.is_not(None),
            DiscoveryJob.next_run_at <= now,
        ).order_by(DiscoveryJob.next_run_at.asc()).limit(limit).with_for_update(skip_locked=True)
    )).all())
    ids=[]
    for row in rows:
        ids.append(row.id)
        row.next_run_at = now + timedelta(minutes=row.interval_minutes)
    await db.commit()
    return ids
