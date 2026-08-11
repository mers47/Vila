from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import SalesHandoff

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/handoffs")
async def list_handoffs(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(SalesHandoff).order_by(SalesHandoff.created_at.desc()))
    return result.scalars().all()


@router.post("/handoffs/{handoff_id}/claim")
async def claim_handoff(handoff_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from datetime import datetime, timezone
    handoff = await db.get(SalesHandoff, handoff_id)
    if not handoff:
        return {"status": "not_found"}
    handoff.status = "CLAIMED"
    handoff.assigned_to_user_id = user.id
    handoff.claimed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "claimed"}