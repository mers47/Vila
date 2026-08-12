from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.entities import SalesHandoff, Lead, User
from app.services.audit import audit

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/handoffs")
async def handoffs(status: str | None = "NEW", db: AsyncSession = Depends(get_db), _: User = Depends(require_roles("admin", "sales", "supervisor"))):
    stmt = select(SalesHandoff).order_by(SalesHandoff.created_at.desc()).limit(200)
    if status:
        stmt = stmt.where(SalesHandoff.status == status)
    rows = list((await db.scalars(stmt)).all())
    out=[]
    for h in rows:
        lead=await db.get(Lead,h.lead_id)
        out.append({"id":str(h.id),"lead_id":str(h.lead_id),"business_name":lead.business_name if lead else None,
                    "reason":h.reason,"status":h.status,"assigned_to_user_id":str(h.assigned_to_user_id) if h.assigned_to_user_id else None,
                    "created_at":h.created_at})
    return out


@router.post("/handoffs/{handoff_id}/claim")
async def claim(handoff_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "sales", "supervisor"))):
    row=await db.get(SalesHandoff,handoff_id)
    if not row: raise HTTPException(404,"handoff not found")
    if row.status not in {"NEW","CLAIMED"}: raise HTTPException(409,"handoff is already closed")
    row.assigned_to_user_id=user.id; row.status="CLAIMED"; row.claimed_at=datetime.now(timezone.utc)
    lead=await db.get(Lead,row.lead_id)
    if lead: lead.assigned_to_user_id=user.id; lead.status="HANDED_TO_SALES"
    await audit(db, action="sales_handoff.claimed", entity_type="sales_handoff", entity_id=str(row.id), actor_user_id=user.id, detail={"lead_id": str(row.lead_id)})
    await db.commit(); return {"status":"CLAIMED","assigned_to_user_id":str(user.id)}


class CloseIn(BaseModel):
    note: str | None = None


@router.post("/handoffs/{handoff_id}/close")
async def close(handoff_id: UUID, payload: CloseIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "sales", "supervisor"))):
    row=await db.get(SalesHandoff,handoff_id)
    if not row: raise HTTPException(404,"handoff not found")
    row.status="CLOSED"; row.note=payload.note; row.resolved_at=datetime.now(timezone.utc)
    await audit(db, action="sales_handoff.closed", entity_type="sales_handoff", entity_id=str(row.id), actor_user_id=user.id)
    await db.commit(); return {"status":"CLOSED"}
