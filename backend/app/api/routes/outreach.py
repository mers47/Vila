from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.outreach import queue_outbound

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/send")
async def send_message(
    lead_id: UUID,
    contact_id: UUID,
    text: str,
    campaign_id: UUID | None = None,
    idempotency_key: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    msg = await queue_outbound(db, lead_id=lead_id, contact_id=contact_id, text=text, campaign_id=campaign_id, idempotency_key=idempotency_key)
    await db.commit()
    return {"message_id": str(msg.id), "status": msg.status, "error_code": msg.error_code}