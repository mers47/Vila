from abc import ABC, abstractmethod

from app.connectors.result import SendResult


class BaseConnector(ABC):
    @abstractmethod
    async def send_text(self, to: str, text: str) -> SendResult:
        ...

    @abstractmethod
    async def send_template(self, to: str, template_name: str, language: str, components: list | None = None) -> SendResult:
        ...

    @abstractmethod
    async def get_status(self, message_id: str) -> SendResult:
        ...