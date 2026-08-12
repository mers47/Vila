from dataclasses import dataclass

DEFAULT_WEIGHTS = {
    "industry_match": 25,
    "city_match": 15,
    "active_online": 10,
    "has_contact": 10,
    "has_social": 10,
    "product_match": 15,
    "suitable_size": 10,
    "need_signal": 5,
}


@dataclass(frozen=True)
class ScoreResult:
    score: int
    temperature: str
    reasons: list[str]


def score_lead(*, industry_match: bool, city_match: bool, active_online: bool,
               has_contact: bool, has_social: bool, product_match: bool,
               suitable_size: bool, need_signal: bool, weights: dict | None = None) -> ScoreResult:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    values = {
        "industry_match": industry_match,
        "city_match": city_match,
        "active_online": active_online,
        "has_contact": has_contact,
        "has_social": has_social,
        "product_match": product_match,
        "suitable_size": suitable_size,
        "need_signal": need_signal,
    }
    score = sum(int(weights.get(key, 0)) for key, enabled in values.items() if enabled)
    score = max(0, min(score, 100))
    temp = "HOT" if score >= 80 else "WARM" if score >= 60 else "COLD"
    return ScoreResult(score, temp, [key for key, enabled in values.items() if enabled])
