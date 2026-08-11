TEMPLATES = {
    "fa": {
        "intro": "سلام {business_name} عزیز،\nما {company_name} هستیم و خدمات بازاریابی ارائه میدیم.\nاگر تمایل داشتید، خوشحال میشیم بیشتر صحبت کنیم.",
        "follow_up": "سلام مجدد {business_name} جان،\nپیام قبلی ما رو دریافت کردید؟ خوشحال میشیم بدونیم نظرتون چیه.",
    }
}


def render_template(name: str, language: str = "fa", **variables) -> str:
    tmpl = TEMPLATES.get(language, {}).get(name, "")
    if not tmpl:
        return ""
    try:
        return tmpl.format(**variables)
    except KeyError:
        return tmpl