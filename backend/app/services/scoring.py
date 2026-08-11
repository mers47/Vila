from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ScoringProfile


async def get_active_profile(db: AsyncSession) -> ScoringProfile | None:
    return await db.scalar(select(ScoringProfile).where(ScoringProfile.is_active == True))