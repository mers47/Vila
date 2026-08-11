from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.entities import Message, MessageAttempt, OutboxEvent
from app.services.rate_limit import circuit_delay

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/dashboard")
async def ops_dashboard(db: AsyncSession = Depends(get_db), user=Depends(get_current_admin)):
    failed_msgs = await db.scalar(select(func.count(Message.id)).where(Message.status == "FAILED"))
    pending_outbox = await db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.status == "PENDING"))

    circuits = {}
    for provider in ["WHATSAPP", "INSTAGRAM", "TELEGRAM", "EITAA", "RUBIKA"]:
        d = await circuit_delay(provider)
        circuits[provider] = {"open": d > 0, "retry_in_seconds": d}

    return {"failed_messages": failed_msgs or 0, "pending_outbox_events": pending_outbox or 0, "circuit_breakers": circuits}