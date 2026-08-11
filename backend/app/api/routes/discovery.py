from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.connectors.google_places import GooglePlacesConnector
from app.db.session import get_db

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/google-places")
async def search_google_places(query: str, city: str | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    connector = GooglePlacesConnector()
    results = await connector.nearby_search(query=query, city=city, max_results=20)
    return {"results": results, "total": len(results)}