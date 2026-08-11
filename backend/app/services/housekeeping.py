from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.entities import OutboxEvent, UserSession


async def cleanup_outbox(db: AsyncSession):
    s = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=s.outbox_retention_days)
    await db.execute(delete(OutboxEvent).where(OutboxEvent.created_at < cutoff))
    await db.commit()


async def cleanup_revoked_sessions(db: AsyncSession):
    s = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=s.revoked_session_retention_days)
    await db.execute(delete(UserSession).where(UserSession.revoked_at < cutoff))
    await db.commit()