from dataclasses import dataclass, field


@dataclass
class SendResult:
    success: bool
    external_id: str | None = None
    status: str = "UNKNOWN"
    http_status: int | None = None
    error_code: str | None = None
    error_detail: str | None = None
    retry_after_seconds: int | None = None
    raw: dict = field(default_factory=dict)