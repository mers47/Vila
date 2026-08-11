from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit_logs"])


@router.get("/")
async def list_logs(limit: int = Query(default=50, le=200), offset: int = 0, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit))
    return result.scalars().all()