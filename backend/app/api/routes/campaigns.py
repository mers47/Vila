from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Campaign
from app.schemas.campaigns import CampaignCreate, CampaignResponse

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/enroll/{lead_id}")
async def enroll_lead(campaign_id: UUID, lead_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.services.campaign_engine import enroll_lead as do_enroll
    result = await do_enroll(db, lead_id, campaign_id)
    if not result:
        raise HTTPException(status_code=400, detail="Enrollment failed — check score or contacts")
    await db.commit()
    return {"status": "enrolled", "campaign_lead_id": str(result.id)}