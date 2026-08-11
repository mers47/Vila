from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditLog


async def log_audit(db: AsyncSession, action: str, entity_type: str, entity_id: str | None = None, actor_user_id: UUID | None = None, detail: dict | None = None):
    db.add(AuditLog(action=action, entity_type=entity_type, entity_id=entity_id, actor_user_id=actor_user_id, detail=detail or {}))
    await db.flush()