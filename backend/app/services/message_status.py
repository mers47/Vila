from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Message


async def update_message_status(db: AsyncSession, external_message_id: str, status: str, error_code: str | None = None, error_detail: str | None = None):
    msg = await db.scalar(select(Message).where(Message.external_message_id == external_message_id))
    if not msg:
        return None
    msg.status = status
    if error_code:
        msg.error_code = error_code
    if error_detail:
        msg.error_detail = error_detail
    await db.flush()
    return msg