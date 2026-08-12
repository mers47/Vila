from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Message

STATUS_MAP = {"sent": "SENT", "delivered": "DELIVERED", "read": "READ", "failed": "FAILED"}


async def update_external_status(
    db: AsyncSession,
    external_message_id: str,
    status: str,
    error_detail: str | None = None,
    *,
    commit: bool = True,
) -> bool:
    msg = await db.scalar(select(Message).where(Message.external_message_id == external_message_id))
    if not msg:
        return False
    mapped = STATUS_MAP.get(status.lower())
    now = datetime.now(timezone.utc)
    if mapped:
        msg.status = mapped
        if mapped == "SENT" and msg.sent_at is None:
            msg.sent_at = now
        elif mapped == "DELIVERED":
            msg.delivered_at = now
        elif mapped == "READ":
            msg.delivered_at = msg.delivered_at or now
            msg.read_at = now
    if error_detail:
        msg.error_detail = error_detail[:2000]
    if commit:
        await db.commit()
    return True
