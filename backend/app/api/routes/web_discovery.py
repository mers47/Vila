from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.web_ingest import ingest_website

router = APIRouter(prefix="/web-discovery", tags=["web_discovery"])


@router.post("/ingest")
async def ingest_url(url: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await ingest_website(url)
    if not result:
        return {"status": "failed", "reason": "url_blocked_or_unreachable"}
    return {"status": "ok", "data": result}