from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Lead, ScoringProfile
from app.services.lead_scoring import score_lead
from app.services.scoring import get_active_profile

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/recalculate/{lead_id}")
async def recalculate(lead_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404)
    profile = await get_active_profile(db)
    if not profile:
        raise HTTPException(status_code=400, detail="No active scoring profile")
    new_score = score_lead(lead, profile)
    lead.score = new_score
    await db.commit()
    return {"lead_id": str(lead_id), "score": new_score}