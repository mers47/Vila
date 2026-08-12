from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import AuditLog


async def audit(db: AsyncSession, *, action: str, entity_type: str, entity_id: str | None,
                actor_user_id=None, detail: dict | None = None) -> None:
    db.add(AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
    ))
