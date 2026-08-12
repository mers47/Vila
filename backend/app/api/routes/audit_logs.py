from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
async def list_audit_logs(
    action: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin", "supervisor")),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = list((await db.scalars(stmt)).all())
    return [{
        "id": str(x.id), "actor_user_id": str(x.actor_user_id) if x.actor_user_id else None,
        "action": x.action, "entity_type": x.entity_type, "entity_id": x.entity_id,
        "detail": x.detail, "created_at": x.created_at,
    } for x in rows]
