from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.entities import Campaign, CampaignLead, User
from app.schemas.campaigns import CampaignCreate, CampaignOut
from app.services.campaign_engine import enroll_campaign
from app.services.audit import audit

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    return list((await db.scalars(select(Campaign).order_by(Campaign.created_at.desc()))).all())


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "marketing", "supervisor"))):
    campaign = Campaign(**payload.model_dump())
    db.add(campaign); await db.flush()
    await audit(db, action="campaign.created", entity_type="campaign", entity_id=str(campaign.id), actor_user_id=user.id)
    await db.commit(); await db.refresh(campaign); return campaign


@router.post("/{campaign_id}/activate")
async def activate(campaign_id: UUID, limit: int = Query(5000, ge=1, le=20000), db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "marketing", "supervisor"))):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign: raise HTTPException(404, "campaign not found")
    if campaign.status == "PAUSED": raise HTTPException(409, "campaign is paused")
    result = await enroll_campaign(db, campaign, limit)
    await audit(db, action="campaign.activated", entity_type="campaign", entity_id=str(campaign.id), actor_user_id=user.id, detail=result)
    await db.commit()
    return result


@router.post("/{campaign_id}/pause")
async def pause(campaign_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "marketing", "supervisor"))):
    campaign=await db.get(Campaign,campaign_id)
    if not campaign: raise HTTPException(404,"campaign not found")
    campaign.status="PAUSED"
    await db.execute(CampaignLead.__table__.update().where(CampaignLead.campaign_id==campaign.id, CampaignLead.status=="ACTIVE").values(status="PAUSED"))
    await audit(db, action="campaign.paused", entity_type="campaign", entity_id=str(campaign.id), actor_user_id=user.id)
    await db.commit(); return {"status":"PAUSED"}


@router.post("/{campaign_id}/resume")
async def resume(campaign_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "marketing", "supervisor"))):
    campaign=await db.get(Campaign,campaign_id)
    if not campaign: raise HTTPException(404,"campaign not found")
    campaign.status="ACTIVE"
    await db.execute(CampaignLead.__table__.update().where(CampaignLead.campaign_id==campaign.id, CampaignLead.status=="PAUSED").values(status="ACTIVE"))
    await audit(db, action="campaign.resumed", entity_type="campaign", entity_id=str(campaign.id), actor_user_id=user.id)
    await db.commit(); return {"status":"ACTIVE"}


@router.get("/{campaign_id}/stats")
async def stats(campaign_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    rows=(await db.execute(select(CampaignLead.status, func.count()).where(CampaignLead.campaign_id==campaign_id).group_by(CampaignLead.status))).all()
    return {status:count for status,count in rows}
