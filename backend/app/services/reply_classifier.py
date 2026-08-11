def classify_reply(text: str) -> tuple[str, int]:
    t = text.strip().lower()

    optout_keywords = ["لغو", "حذف", "تماس نگیرید", "پیام ندهید", "stop", "cancel", "unsubscribe", "قطع کن", "دیگه پیام نده"]
    positive_keywords = ["بله", "موافقم", "اطلاعات", "بفرمایید", "بگید", "interested", "yes", "ok", "آره", "خوبه", "قیمت", "هزینه", "تعرفه"]
    question_keywords = ["چطور", "چه", "کجا", "کی", "چرا", "آیا", "؟", "?"]

    for kw in optout_keywords:
        if kw in t:
            return "OPTOUT", 90

    for kw in positive_keywords:
        if kw in t:
            return "POSITIVE", 75

    for kw in question_keywords:
        if kw in t:
            return "QUESTION", 70

    return "NEUTRAL", 50