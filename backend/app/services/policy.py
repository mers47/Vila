from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from app.models.enums import ConsentStatus


@dataclass(frozen=True)
class Eligibility:
    allowed: bool
    reason: str


def _within_24h(last_inbound_at: datetime | None) -> bool:
    if not last_inbound_at:
        return False
    if last_inbound_at.tzinfo is None:
        last_inbound_at = last_inbound_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_inbound_at <= timedelta(hours=24)


def can_send(
    channel: str,
    consent_status: str,
    *,
    message_kind: str = "text",
    interaction_started: bool = False,
    last_inbound_at: datetime | None = None,
) -> Eligibility:
    channel = channel.upper()
    message_kind = message_kind.lower()
    if consent_status == ConsentStatus.OPTED_OUT.value:
        return Eligibility(False, "recipient opted out")

    if channel == "WHATSAPP":
        if message_kind in {"template", "marketing_template"}:
            if consent_status != ConsentStatus.OPTED_IN.value:
                return Eligibility(False, "whatsapp template outreach requires recorded opt-in")
            return Eligibility(True, "eligible whatsapp template outreach")
        if not _within_24h(last_inbound_at):
            return Eligibility(False, "whatsapp free-form text requires an active customer-service window")
        return Eligibility(True, "eligible whatsapp service message")

    if channel == "INSTAGRAM":
        if not _within_24h(last_inbound_at):
            return Eligibility(False, "instagram free-form messaging requires an eligible recent interaction")
        return Eligibility(True, "eligible instagram conversation")

    if channel in {"TELEGRAM", "RUBIKA"}:
        if not interaction_started:
            return Eligibility(False, f"{channel.lower()} bot requires the user to start/interact first")
        return Eligibility(True, "eligible bot conversation")

    if channel == "EITAA":
        if consent_status != ConsentStatus.OPTED_IN.value:
            return Eligibility(False, "eitaa requires user-granted send access")
        return Eligibility(True, "eligible eitaa contact")

    return Eligibility(False, "channel is not enabled for automated messaging")
