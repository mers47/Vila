from app.connectors.public_web import PublicBusinessPage
from app.services.url_safety import social_handle, whatsapp_number
from app.schemas.leads import LeadCreate, ContactIn


def page_to_payload(page: PublicBusinessPage, *, source: str, source_external_id: str | None = None) -> LeadCreate:
    contacts: list[ContactIn] = []
    for phone in page.phones:
        contacts.append(ContactIn(channel="PHONE", value=phone))
    wa = whatsapp_number(page.whatsapp)
    if wa:
        contacts.append(ContactIn(channel="WHATSAPP", value=wa))
    ig = social_handle(page.instagram)
    if ig:
        contacts.append(ContactIn(channel="INSTAGRAM_HANDLE", value=ig))
    tg = social_handle(page.telegram)
    if tg:
        contacts.append(ContactIn(channel="TELEGRAM_HANDLE", value=tg))
    contacts.append(ContactIn(channel="WEB", value=page.url))
    return LeadCreate(
        business_name=(page.title or page.url)[:255],
        website=page.url,
        source=source,
        source_external_id=source_external_id or page.url,
        contacts=contacts,
        metadata_json={"instagram_url": page.instagram, "telegram_url": page.telegram, "whatsapp_url": page.whatsapp},
    )
