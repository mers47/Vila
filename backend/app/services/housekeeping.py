from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.entities import OutboxEvent, UserSession


async def run_housekeeping(db: AsyncSession) -> dict[str, int]:
    """Prune transport/session metadata only.

    MessageAttempt/AuditLog retention is intentionally not hard-coded because those records
    can have contractual/compliance value. The business must set that policy explicitly.
    """
    s = get_settings()
    now = datetime.now(timezone.utc)
    outbox_before = now - timedelta(days=max(1, s.outbox_retention_days))
    session_before = now - timedelta(days=max(1, s.revoked_session_retention_days))

    outbox_result = await db.execute(
        delete(OutboxEvent).where(
            OutboxEvent.status.in_(["DONE", "CANCELLED"]),
            OutboxEvent.updated_at < outbox_before,
        )
    )
    session_result = await db.execute(
        delete(UserSession).where(
            UserSession.revoked_at.is_not(None),
            UserSession.revoked_at < session_before,
        )
    )
    expired_result = await db.execute(
        delete(UserSession).where(
            UserSession.expires_at < session_before,
        )
    )
    await db.commit()
    return {
        "outbox_deleted": int(outbox_result.rowcount or 0),
        "revoked_sessions_deleted": int(session_result.rowcount or 0),
        "expired_sessions_deleted": int(expired_result.rowcount or 0),
    }
