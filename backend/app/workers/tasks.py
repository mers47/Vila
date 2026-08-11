from uuid import UUID

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.entities import CampaignLead, DiscoveryJob, OutboxEvent
from app.services.discovery_jobs import run_discovery_job
from app.services.housekeeping import cleanup_outbox, cleanup_revoked_sessions
from app.services.outreach import dispatch_message
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_outbox")
async def process_outbox():
    async with AsyncSessionLocal() as db:
        events = (await db.execute(select(OutboxEvent).where(OutboxEvent.status == "PENDING").limit(50))).scalars().all()
        for event in events:
            if event.topic == "outbound.send":
                message_id = event.payload.get("message_id")
                if message_id:
                    await dispatch_message(db, UUID(message_id))
                    event.status = "PROCESSED"
        await db.commit()


@celery_app.task(name="app.workers.tasks.dispatch_outbound")
async def dispatch_outbound(message_id: str):
    async with AsyncSessionLocal() as db:
        await dispatch_message(db, UUID(message_id))
        await db.commit()


@celery_app.task(name="app.workers.tasks.run_discovery")
async def run_discovery(job_id: str):
    async with AsyncSessionLocal() as db:
        await run_discovery_job(db, UUID(job_id))
        await db.commit()


@celery_app.task(name="app.workers.tasks.tick_discovery")
async def tick_discovery():
    async with AsyncSessionLocal() as db:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        due_jobs = (await db.execute(select(DiscoveryJob).where(DiscoveryJob.is_enabled == True, DiscoveryJob.next_run_at <= now))).scalars().all()
        for job in due_jobs:
            run_discovery.delay(str(job.id))


@celery_app.task(name="app.workers.tasks.run_housekeeping")
async def run_housekeeping():
    async with AsyncSessionLocal() as db:
        await cleanup_outbox(db)
        await cleanup_revoked_sessions(db)