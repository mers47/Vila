from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.entities import DiscoveryJob, User
from app.services.audit import audit
from app.workers.tasks import run_discovery_job

router = APIRouter(prefix="/discovery-jobs", tags=["discovery"])


class DiscoveryJobIn(BaseModel):
    source: Literal["GOOGLE_PLACES", "PUBLIC_WEB"] = "GOOGLE_PLACES"
    query: str = Field(min_length=2, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    max_results: int = Field(default=60, ge=1, le=100)
    interval_minutes: int = Field(default=1440, ge=60, le=43200)
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_source(self):
        if self.source == "GOOGLE_PLACES" and self.max_results > 60:
            raise ValueError("Google Places Text Search supports at most 60 results across pages")
        if self.source == "PUBLIC_WEB" and not self.query.startswith(("https://", "http://")):
            raise ValueError("PUBLIC_WEB query must be a public http/https seed URL")
        return self


@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    rows=list((await db.scalars(select(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()))).all())
    return [{"id":str(x.id),"source":x.source,"query":x.query,"city":x.city,"max_results":x.max_results,
             "interval_minutes":x.interval_minutes,"is_enabled":x.is_enabled,"last_run_at":x.last_run_at,
             "next_run_at":x.next_run_at,"last_result_count":x.last_result_count,"last_error":x.last_error} for x in rows]


@router.post("", status_code=201)
async def create_job(payload: DiscoveryJobIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin","marketing","supervisor"))):
    row=DiscoveryJob(source=payload.source, query=payload.query, city=payload.city, max_results=payload.max_results,
                     interval_minutes=payload.interval_minutes, is_enabled=payload.is_enabled,
                     next_run_at=datetime.now(timezone.utc) if payload.is_enabled else None, created_by_user_id=user.id)
    db.add(row); await db.flush()
    await audit(db, action="discovery_job.created", entity_type="discovery_job", entity_id=str(row.id), actor_user_id=user.id,
                detail={"source":row.source,"query":row.query})
    await db.commit(); await db.refresh(row)
    return {"id":str(row.id),"next_run_at":row.next_run_at}


@router.post("/{job_id}/run", status_code=202)
async def run_now(job_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin","marketing","supervisor"))):
    if not await db.get(DiscoveryJob, job_id): raise HTTPException(404,"discovery job not found")
    task=run_discovery_job.delay(str(job_id))
    await audit(db, action="discovery_job.queued", entity_type="discovery_job", entity_id=str(job_id), actor_user_id=user.id, detail={"task_id":task.id})
    await db.commit(); return {"queued":True,"task_id":task.id}


@router.post("/{job_id}/toggle")
async def toggle(job_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin","marketing","supervisor"))):
    row=await db.get(DiscoveryJob,job_id)
    if not row: raise HTTPException(404,"discovery job not found")
    row.is_enabled=not row.is_enabled
    row.next_run_at=datetime.now(timezone.utc) if row.is_enabled else None
    await audit(db, action="discovery_job.toggled", entity_type="discovery_job", entity_id=str(row.id), actor_user_id=user.id, detail={"is_enabled":row.is_enabled})
    await db.commit(); return {"is_enabled":row.is_enabled,"next_run_at":row.next_run_at}
