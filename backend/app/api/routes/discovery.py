from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_roles
from app.connectors.google_places import GooglePlacesConnector
from app.connectors.instagram_discovery import InstagramBusinessDiscoveryConnector
from app.db.session import get_db
from app.models.entities import User
from app.schemas.leads import LeadCreate, ContactIn
from app.services.lead_upsert import upsert_lead
from app.services.lead_scoring import apply_active_profile

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/google-places")
async def discover_google_places(
    query: str = Query(min_length=2, max_length=200),
    city: str | None = None,
    max_results: int = Query(60, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "marketing", "supervisor")),
):
    full_query = f"{query} {city}" if city else query
    places = await GooglePlacesConnector().text_search(full_query, max_results=max_results)
    created = []
    for p in places:
        display = p.get("displayName", {}).get("text") or "Unknown business"
        contacts = []
        phone = p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber")
        if phone:
            contacts.append(ContactIn(channel="PHONE", value=phone))
        if p.get("websiteUri"):
            contacts.append(ContactIn(channel="WEB", value=p["websiteUri"]))
        lead, _ = await upsert_lead(db, LeadCreate(
            business_name=display,
            industry=p.get("primaryType"),
            city=city,
            address=p.get("formattedAddress"),
            website=p.get("websiteUri"),
            source="GOOGLE_PLACES",
            source_external_id=p.get("id"),
            contacts=contacts,
            metadata_json={"business_status": p.get("businessStatus")},
        ), actor_user_id=user.id)
        await apply_active_profile(db, lead, has_contact=bool(contacts), has_social=False)
        created.append(str(lead.id))
    await db.commit()
    return {"query": full_query, "found": len(places), "lead_ids": created}


@router.post("/instagram-business")
async def discover_instagram_business(
    username: str = Query(min_length=1, max_length=30),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "marketing", "supervisor")),
):
    profile = await InstagramBusinessDiscoveryConnector().lookup(username)
    if not profile:
        return {"found": False, "username": username}
    handle = profile.get("username") or username.lstrip("@")
    contacts = [ContactIn(channel="INSTAGRAM_HANDLE", value=handle)]
    if profile.get("website"):
        contacts.append(ContactIn(channel="WEB", value=profile["website"]))
    lead, _ = await upsert_lead(db, LeadCreate(
        business_name=profile.get("name") or handle,
        website=profile.get("website"),
        source="INSTAGRAM_BUSINESS_DISCOVERY",
        source_external_id=str(profile.get("id") or handle),
        contacts=contacts,
        metadata_json={
            "username": handle, "biography": profile.get("biography"),
            "followers_count": profile.get("followers_count"), "media_count": profile.get("media_count"),
            "profile_picture_url": profile.get("profile_picture_url"),
        },
    ), actor_user_id=user.id)
    await apply_active_profile(db, lead, has_contact=True, has_social=True)
    await db.commit()
    return {"found": True, "lead_id": str(lead.id), "username": handle}
