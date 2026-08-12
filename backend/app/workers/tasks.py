from uuid import UUID

from app.db.session import SessionLocal
from app.services.campaign_engine import process_due_campaign_leads
from app.services.discovery_jobs import execute_discovery_job, due_job_ids
from app.services.outreach import claim_outbox, deliver_outbox_event
from app.services.housekeeping import run_housekeeping
from app.workers.async_runner import run_async
from app.workers.celery_app import celery_app


async def _process_campaign_queue():
    async with SessionLocal() as db:
        return await process_due_campaign_leads(db)


@celery_app.task(name="app.workers.tasks.process_campaign_queue")
def process_campaign_queue():
    return run_async(_process_campaign_queue(), timeout=110)


async def _run_discovery_job(job_id: str):
    async with SessionLocal() as db:
        return await execute_discovery_job(db, UUID(job_id))


@celery_app.task(
    name="app.workers.tasks.run_discovery_job",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 4},
    soft_time_limit=280,
    time_limit=300,
)
def run_discovery_job(job_id: str):
    return run_async(_run_discovery_job(job_id), timeout=275)


async def _scan_discovery_jobs():
    async with SessionLocal() as db:
        return await due_job_ids(db)


@celery_app.task(name="app.workers.tasks.scan_discovery_jobs")
def scan_discovery_jobs():
    ids = run_async(_scan_discovery_jobs(), timeout=30)
    queued = 0
    for job_id in ids:
        run_discovery_job.delay(str(job_id))
        queued += 1
    return queued


async def _claim_outbox():
    async with SessionLocal() as db:
        return await claim_outbox(db)


@celery_app.task(name="app.workers.tasks.drain_outbox")
def drain_outbox():
    claimed = run_async(_claim_outbox(), timeout=30)
    published = 0
    for event_id, lease_token in claimed:
        try:
            deliver_outbox_event_task.delay(str(event_id), lease_token)
            published += 1
        except Exception:
            continue
    return published


async def _deliver_outbox(event_id: str, lease_token: str):
    async with SessionLocal() as db:
        return await deliver_outbox_event(db, UUID(event_id), lease_token)


@celery_app.task(name="app.workers.tasks.deliver_outbox_event")
def deliver_outbox_event_task(event_id: str, lease_token: str):
    return run_async(_deliver_outbox(event_id, lease_token), timeout=110)


async def _housekeeping():
    async with SessionLocal() as db:
        return await run_housekeeping(db)


@celery_app.task(name="app.workers.tasks.housekeeping")
def housekeeping():
    return run_async(_housekeeping(), timeout=110)
