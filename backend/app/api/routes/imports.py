from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Lead

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/bulk")
async def bulk_import(leads: list[dict], db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    count = 0
    for item in leads:
        lead = Lead(business_name=item.get("business_name", "Unknown"), source="BULK_IMPORT", industry=item.get("industry"), city=item.get("city"), website=item.get("website"))
        db.add(lead)
        count += 1
    await db.commit()
    return {"imported": count}