from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import DiscoveryJob

router = APIRouter(prefix="/discovery-jobs", tags=["discovery_jobs"])


@router.get("/")
async def list_jobs(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()))
    return result.scalars().all()


@router.post("/")
async def create_job(source: str, query: str, city: str | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    job = DiscoveryJob(source=source, query=query, city=city, created_by_user_id=user.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return {"id": str(job.id), "status": "created"}