from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import ContactPoint, Suppression, User
from app.services.audit import audit

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ConsentIn(BaseModel):
    status: Literal["UNKNOWN", "OPTED_IN", "OPTED_OUT"]
    source: str | None = Field(default=None, max_length=120)


class ReactivateIn(BaseModel):
    source: str = Field(min_length=3, max_length=120)


@router.post("/{contact_id}/consent")
async def set_consent(
    contact_id: UUID,
    payload: ConsentIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "marketing", "supervisor")),
):
    contact = await db.get(ContactPoint, contact_id)
    if not contact:
        raise HTTPException(404, "contact not found")
    if payload.status == "OPTED_IN" and not payload.source:
        raise HTTPException(422, "consent source is required for OPTED_IN")
    contact.consent_status = payload.status
    contact.consent_source = payload.source
    contact.consent_at = datetime.now(timezone.utc) if payload.status in {"OPTED_IN", "OPTED_OUT"} else None
    if payload.status == "OPTED_OUT":
        existing = await db.scalar(select(Suppression).where(
            Suppression.channel == contact.channel,
            Suppression.value_normalized == contact.value_normalized,
        ))
        if not existing:
            db.add(Suppression(channel=contact.channel, value_normalized=contact.value_normalized,
                               reason="operator-recorded opt-out"))
    await audit(db, action="contact.consent_changed", entity_type="contact_point", entity_id=str(contact.id),
                actor_user_id=user.id, detail={"status":payload.status,"source":payload.source,"channel":contact.channel})
    await db.commit()
    return {"id":str(contact.id),"consent_status":contact.consent_status,"consent_source":contact.consent_source}


@router.post("/{contact_id}/reactivate")
async def reactivate(
    contact_id: UUID,
    payload: ReactivateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "supervisor")),
):
    contact = await db.get(ContactPoint, contact_id)
    if not contact:
        raise HTTPException(404, "contact not found")
    contact.consent_status = "OPTED_IN"
    contact.consent_source = payload.source
    contact.consent_at = datetime.now(timezone.utc)
    await db.execute(delete(Suppression).where(
        Suppression.channel == contact.channel,
        Suppression.value_normalized == contact.value_normalized,
    ))
    await audit(db, action="contact.reactivated", entity_type="contact_point", entity_id=str(contact.id),
                actor_user_id=user.id, detail={"source":payload.source,"channel":contact.channel})
    await db.commit()
    return {"id":str(contact.id),"consent_status":"OPTED_IN"}
