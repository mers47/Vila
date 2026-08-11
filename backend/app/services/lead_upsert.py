from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Lead


async def upsert_lead(db: AsyncSession, *, business_name: str, source: str, source_external_id: str | None = None, **fields) -> Lead:
    values = {"business_name": business_name, "source": source, "source_external_id": source_external_id, **fields}
    stmt = pg_insert(Lead).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_external_id"],
        set_={k: v for k, v in values.items() if k not in ("source", "source_external_id", "business_name")},
    ).returning(Lead)
    result = await db.execute(stmt)
    return result.scalar_one()