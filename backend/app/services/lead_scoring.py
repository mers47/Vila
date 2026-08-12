from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Lead, ScoringProfile
from app.services.scoring import score_lead


async def apply_active_profile(db: AsyncSession, lead: Lead, *, has_contact: bool, has_social: bool = False) -> None:
    profile = await db.scalar(select(ScoringProfile).where(ScoringProfile.is_active.is_(True)).order_by(ScoringProfile.updated_at.desc()))
    target_industries = [x.lower() for x in (profile.target_industries if profile else [])]
    target_cities = [x.lower() for x in (profile.target_cities if profile else [])]
    industry_match = not target_industries or bool(lead.industry and lead.industry.lower() in target_industries)
    city_match = not target_cities or bool(lead.city and lead.city.lower() in target_cities)
    result = score_lead(
        industry_match=industry_match,
        city_match=city_match,
        active_online=bool(lead.website),
        has_contact=has_contact,
        has_social=has_social,
        product_match=industry_match,
        suitable_size=False,
        need_signal=False,
        weights=profile.weights if profile else None,
    )
    lead.score = result.score
    lead.temperature = result.temperature
    lead.metadata_json = {**(lead.metadata_json or {}), "score_reasons": result.reasons}
    if result.score >= 60 and lead.status == "NEW":
        lead.status = "QUALIFIED"
