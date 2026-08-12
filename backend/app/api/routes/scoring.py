from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.entities import ScoringProfile, User
from app.services.scoring import DEFAULT_WEIGHTS
from app.services.audit import audit

router = APIRouter(prefix="/scoring", tags=["scoring"])


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    weights: dict[str, int] = Field(default_factory=lambda: DEFAULT_WEIGHTS.copy())
    target_industries: list[str] = []
    target_cities: list[str] = []
    is_active: bool = True


@router.get("/profiles")
async def profiles(db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    rows = list((await db.scalars(select(ScoringProfile).order_by(ScoringProfile.created_at.desc()))).all())
    return [{"id": str(x.id), "name": x.name, "is_active": x.is_active, "weights": x.weights,
             "target_industries": x.target_industries, "target_cities": x.target_cities} for x in rows]


@router.post("/profiles", status_code=201)
async def create_profile(payload: ProfileIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "supervisor"))):
    if any(v < 0 or v > 100 for v in payload.weights.values()):
        raise HTTPException(422, "weights must be between 0 and 100")
    if payload.is_active:
        await db.execute(update(ScoringProfile).values(is_active=False))
    row = ScoringProfile(**payload.model_dump())
    db.add(row)
    await db.flush()
    await audit(db, action="scoring_profile.created", entity_type="scoring_profile", entity_id=str(row.id), actor_user_id=user.id, detail={"is_active": row.is_active})
    await db.commit(); await db.refresh(row)
    return {"id": str(row.id), "name": row.name, "is_active": row.is_active}
