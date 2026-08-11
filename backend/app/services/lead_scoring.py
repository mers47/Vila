from app.models.entities import Lead, ScoringProfile


def score_lead(lead: Lead, profile: ScoringProfile) -> int:
    score = 0
    weights = profile.weights or {}

    if profile.target_industries and lead.industry:
        if lead.industry.lower() in [i.lower() for i in profile.target_industries]:
            score += weights.get("industry_match", 25)

    if profile.target_cities and lead.city:
        if lead.city.lower() in [c.lower() for c in profile.target_cities]:
            score += weights.get("city_match", 15)

    if lead.website:
        score += weights.get("active_online", 10)

    if hasattr(lead, 'contacts') and lead.contacts:
        score += weights.get("has_contact", 10)
        for c in lead.contacts:
            if c.channel in ("INSTAGRAM", "TELEGRAM", "EITAA", "RUBIKA"):
                score += weights.get("has_social", 10)
                break

    if lead.metadata_json:
        if lead.metadata_json.get("product_match"):
            score += weights.get("product_match", 15)
        if lead.metadata_json.get("suitable_size"):
            score += weights.get("suitable_size", 10)
        if lead.metadata_json.get("need_signal"):
            score += weights.get("need_signal", 5)

    return min(score, 100)