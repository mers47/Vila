from string import Formatter

ALLOWED_FIELDS = {"business_name", "industry", "city", "province"}


def render_message(template: str, context: dict) -> str:
    fields = {name for _, name, _, _ in Formatter().parse(template) if name}
    unknown = fields - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"unsupported template fields: {sorted(unknown)}")
    safe = {k: str(context.get(k) or "") for k in ALLOWED_FIELDS}
    return template.format(**safe)
