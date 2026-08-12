from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import current_user
from app.db.session import get_db
from app.models.entities import Lead, User, Conversation, Message
from app.schemas.leads import LeadCreate, LeadOut
from app.services.lead_upsert import upsert_lead

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
async def list_leads(
    status: str | None = None,
    city: str | None = None,
    q: str | None = Query(None, min_length=2, max_length=120),
    min_score: int | None = Query(None, ge=0, le=100),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
    before_created_at: datetime | None = None,
    before_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    stmt = select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc()).limit(limit)
    if before_created_at and before_id:
        stmt = stmt.where(tuple_(Lead.created_at, Lead.id) < tuple_(before_created_at, before_id))
    elif offset:
        stmt = stmt.offset(offset)
    if q:
        stmt = stmt.where(Lead.business_name.ilike(f"%{q.strip()}%"))
    if status:
        stmt = stmt.where(Lead.status == status)
    if city:
        stmt = stmt.where(Lead.city == city)
    if min_score is not None:
        stmt = stmt.where(Lead.score >= min_score)
    return list((await db.scalars(stmt)).all())


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    lead, _created = await upsert_lead(db, payload, actor_user_id=user.id)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.get("/stats/summary")
async def lead_stats(db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    total = await db.scalar(select(func.count()).select_from(Lead))
    hot = await db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "HOT"))
    qualified = await db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "QUALIFIED"))
    handed = await db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "HANDED_TO_SALES"))
    return {"total": total or 0, "hot": hot or 0, "qualified": qualified or 0, "handed_to_sales": handed or 0}


@router.get("/followups/candidates")
async def followup_candidates(
    inactive_days: int = Query(30, ge=1, le=3650),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=inactive_days)
    terminal = ["DO_NOT_CONTACT", "NOT_INTERESTED", "HANDED_TO_SALES"]
    stmt = (
        select(Lead)
        .where(
            Lead.status.notin_(terminal),
            (
                (Lead.next_follow_up_at.is_not(None) & (Lead.next_follow_up_at <= now))
                | (Lead.last_contact_at.is_not(None) & (Lead.last_contact_at <= cutoff))
            ),
        )
        .order_by(
            Lead.next_follow_up_at.asc().nullslast(),
            Lead.last_contact_at.asc().nullslast(),
            Lead.score.desc(),
        )
        .limit(limit)
    )
    rows = list((await db.scalars(stmt)).all())
    return [{
        "id": str(lead.id), "business_name": lead.business_name, "city": lead.city,
        "score": lead.score, "status": lead.status, "temperature": lead.temperature,
        "last_contact_at": lead.last_contact_at, "next_follow_up_at": lead.next_follow_up_at,
    } for lead in rows]


@router.get("/{lead_id}")
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    lead = await db.scalar(select(Lead).options(selectinload(Lead.contacts)).where(Lead.id == lead_id))
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    return {
        "id": str(lead.id), "business_name": lead.business_name, "industry": lead.industry,
        "province": lead.province, "city": lead.city, "address": lead.address,
        "website": lead.website, "source": lead.source, "score": lead.score,
        "status": lead.status, "temperature": lead.temperature,
        "next_follow_up_at": lead.next_follow_up_at, "last_contact_at": lead.last_contact_at,
        "contacts": [{"id": str(c.id), "channel": c.channel, "value": c.value,
                      "consent_status": c.consent_status, "consent_source": c.consent_source,
                      "interaction_started": c.interaction_started, "last_inbound_at": c.last_inbound_at} for c in lead.contacts],
    }


@router.get("/{lead_id}/timeline")
async def lead_timeline(lead_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    if not await db.get(Lead, lead_id):
        raise HTTPException(404, "lead not found")
    rows = (await db.execute(
        select(Message, Conversation).join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.lead_id == lead_id).order_by(Message.created_at.desc()).limit(500)
    )).all()
    return [{
        "id": str(msg.id), "channel": conv.channel, "direction": msg.direction, "status": msg.status,
        "body": msg.body, "external_message_id": msg.external_message_id, "error_code": msg.error_code,
        "error_detail": msg.error_detail, "intent_label": msg.intent_label,
        "intent_confidence": msg.intent_confidence, "classification_engine": msg.classification_engine,
        "created_at": msg.created_at,
    } for msg, conv in rows]


@router.get("/{lead_id}/duplicate-candidates")
async def duplicate_candidates(
    lead_id: UUID,
    threshold: float = Query(0.45, ge=0.25, le=0.95),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_user),
):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    similarity = func.similarity(Lead.business_name, lead.business_name)
    stmt = (
        select(Lead, similarity.label("name_similarity"))
        .where(Lead.id != lead.id, similarity >= threshold)
        .order_by(similarity.desc(), Lead.score.desc())
        .limit(limit)
    )
    if lead.city:
        stmt = stmt.where((Lead.city == lead.city) | (similarity >= min(0.80, threshold + 0.20)))
    rows = (await db.execute(stmt)).all()
    return [{
        "id": str(candidate.id),
        "business_name": candidate.business_name,
        "city": candidate.city,
        "website": candidate.website,
        "source": candidate.source,
        "score": candidate.score,
        "name_similarity": round(float(score), 4),
    } for candidate, score in rows]
