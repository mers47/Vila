from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import ContactPoint, Lead

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/lead/{lead_id}")
async def list_contacts(lead_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(ContactPoint).where(ContactPoint.lead_id == lead_id))
    return result.scalars().all()


@router.post("/")
async def add_contact(lead_id: UUID, channel: str, value: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from app.services.normalization import normalize_phone, normalize_username
    norm = normalize_phone(value, channel) if channel == "WHATSAPP" else normalize_username(value)
    contact = ContactPoint(lead_id=lead_id, channel=channel, value=value, value_normalized=norm)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return {"id": str(contact.id), "value_normalized": contact.value_normalized}