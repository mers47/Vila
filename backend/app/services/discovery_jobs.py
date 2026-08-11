from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_places import GooglePlacesConnector
from app.models.entities import DiscoveryJob
from app.services.lead_upsert import upsert_lead


async def run_discovery_job(db: AsyncSession, job_id: UUID):
    job = await db.get(DiscoveryJob, job_id)
    if not job or not job.is_enabled:
        return

    if job.source == "GOOGLE_PLACES":
        connector = GooglePlacesConnector()
        results = await connector.nearby_search(query=job.query, city=job.city, max_results=job.max_results)
        count = 0
        for r in results:
            try:
                await upsert_lead(
                    db,
                    business_name=r["business_name"],
                    source="GOOGLE_PLACES",
                    source_external_id=r.get("place_id"),
                    address=r.get("address"),
                    metadata_json={"rating": r.get("rating"), "types": r.get("types", [])},
                )
                count += 1
            except Exception:
                continue
        job.last_result_count = count
        job.last_error = None
    else:
        job.last_error = f"unsupported source: {job.source}"

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    job.last_run_at = now
    job.next_run_at = now + timedelta(minutes=job.interval_minutes)
    await db.flush()