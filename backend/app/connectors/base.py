from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SendResult:
    success: bool
    external_message_id: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    http_status: int | None = None
    retryable: bool = False
    retry_after_seconds: int | None = None
    latency_ms: int | None = None


class MessagingConnector(ABC):
    @abstractmethod
    async def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
        raise NotImplementedError
