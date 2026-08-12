"""Deterministic, explainable reply classification.

This is intentionally *not* labelled AI.  It is a fast, auditable rules engine used for
safety-critical routing (opt-out / human handoff).  A statistical/LLM classifier can be
added behind the same interface later, but deterministic guardrails remain authoritative.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IntentResult:
    label: str
    confidence: float
    evidence: tuple[str, ...]
    engine: str = "rules-v2"


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").lower().strip()
    value = value.translate(str.maketrans({"ي": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه"}))
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)  # Arabic diacritics
    value = value.replace("\u200c", " ")
    value = re.sub(r"\s+", " ", value)
    return value


RULES: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("OPT_OUT", 0.99, (
        r"پیام\s*(?:ن|ند)ه", r"دیگه\s*پیام\s*ن", r"ارسال\s*نکن", r"مزاحم\s*نش",
        r"لغو", r"حذفم\s*کن", r"stop\b", r"unsubscribe\b", r"do\s*not\s*contact",
    )),
    ("NOT_INTERESTED", 0.94, (
        r"نیاز\s*ندار", r"نمی\s*خوام", r"نمیخوام", r"علاقه\s*ندار", r"تمایل\s*ندار",
        r"ممنون.*نیاز", r"لازم\s*ندار",
    )),
    ("FOLLOW_UP_LATER", 0.90, (
        r"فعلا", r"فعلاً", r"بعدا", r"بعداً", r"هفته\s*بعد", r"ماه\s*بعد",
        r"بعد\s*خبر", r"بعد\s*تماس", r"زمان\s*دیگه", r"بعدتر",
    )),
    ("PURCHASE_INTENT", 0.94, (
        r"لیست\s*قیمت", r"قیمت\s*همکاری", r"شرایط\s*همکاری", r"ثبت\s*سفارش",
        r"خرید\s*عمده", r"سفارش\s*(?:بدم|بدیم|می\s*دم|میدم)", r"فاکتور",
        r"برای\s*خرید", r"چطور\s*سفارش", r"نحوه\s*سفارش", r"تماس\s*(?:بگیر|بگیرید)",
        r"شماره\s*(?:فروش|کارشناس)",
    )),
)

PRICE_ONLY = re.compile(r"(?:^|\s)(?:قیمت|هزینه|تعرفه)(?:\s|[؟?!.]|$)")


def classify_reply_detailed(text: str) -> IntentResult:
    normalized = _normalize(text)
    if not normalized:
        return IntentResult("GENERAL_REPLY", 0.20, ())

    for label, confidence, patterns in RULES:
        matches = tuple(pattern for pattern in patterns if re.search(pattern, normalized))
        if matches:
            adjusted = min(0.99, confidence + max(0, len(matches) - 1) * 0.015)
            return IntentResult(label, adjusted, matches)

    if PRICE_ONLY.search(normalized):
        return IntentResult("PURCHASE_INTENT", 0.78, ("price-term",))

    return IntentResult("GENERAL_REPLY", 0.45, ())


def classify_reply(text: str) -> str:
    return classify_reply_detailed(text).label
