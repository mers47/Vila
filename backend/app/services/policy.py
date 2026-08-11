from app.models.enums import ConsentStatus


def can_send(channel: str, consent_status: str, interaction_started: bool, is_suppressed: bool, is_valid: bool) -> tuple[bool, str | None]:
    if not is_valid:
        return False, "contact_invalid"
    if is_suppressed:
        return False, "suppressed"
    if consent_status == ConsentStatus.OPTED_OUT.value:
        return False, "opted_out"
    if consent_status == ConsentStatus.UNKNOWN.value and not interaction_started:
        return False, "consent_unknown_cold"
    return True, None