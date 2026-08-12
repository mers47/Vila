from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_roles
from app.connectors.public_web import PublicWebConnector
from app.db.session import get_db
from app.models.entities import User
from app.schemas.leads import LeadCreate, ContactIn
from app.services.lead_scoring import apply_active_profile
from app.services.lead_upsert import upsert_lead
from app.services.web_ingest import page_to_payload

router = APIRouter(prefix="/discovery/web", tags=["discovery"])


class WebPageRequest(BaseModel):
    url: HttpUrl


class WebCrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=50, ge=1, le=100)



@router.post("/inspect")
async def inspect_public_business_page(payload: WebPageRequest, _: User = Depends(require_roles("admin", "marketing", "supervisor"))):
    result = await PublicWebConnector().fetch_business_page(str(payload.url))
    return result.__dict__


@router.post("/crawl")
async def crawl_public_business_site(
    payload: WebCrawlRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "marketing", "supervisor")),
):
    pages = await PublicWebConnector().crawl_site(str(payload.url), max_pages=payload.max_pages)
    lead_ids=[]; created=0
    for page in pages:
        lead, was_created = await upsert_lead(db, page_to_payload(page, source="PUBLIC_WEB"), actor_user_id=user.id)
        await apply_active_profile(db, lead, has_contact=bool(page.phones or page.whatsapp),
                                   has_social=bool(page.instagram or page.telegram))
        lead_ids.append(str(lead.id)); created += int(was_created)
    await db.commit()
    return {"pages_with_contacts":len(pages),"created":created,"lead_ids":lead_ids}
