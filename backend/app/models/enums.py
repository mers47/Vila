import enum


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    ENGAGED = "ENGAGED"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    DISQUALIFIED = "DISQUALIFIED"


class Channel(str, enum.Enum):
    WHATSAPP = "WHATSAPP"
    INSTAGRAM = "INSTAGRAM"
    TELEGRAM = "TELEGRAM"
    EITAA = "EITAA"
    RUBIKA = "RUBIKA"


class ConsentStatus(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    OPTED_IN = "OPTED_IN"
    OPTED_OUT = "OPTED_OUT"
    IMPLIED = "IMPLIED"


class MessageDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class MessageStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"
    REJECTED = "REJECTED"