import httpx

from app.connectors.base import BaseConnector
from app.connectors.http import HttpClient
from app.connectors.result import SendResult
from app.core.config import get_settings


class RubikaConnector(BaseConnector):
    def __init__(self):
        s = get_settings()
        self.bot_token = s.rubika_bot_token

    async def send_text(self, to: str, text: str) -> SendResult:
        if not self.bot_token:
            return SendResult(success=False, error_code="NOT_CONFIGURED")
        client = await HttpClient.get_client()
        try:
            resp = await client.post(
                "https://messenger.rubika.ir/api/",
                json={"api_version": "1", "method": "sendMessage", "input": {"bot_token": self.bot_token, "chat_id": to, "text": text}},
            )
            data = resp.json()
            if data.get("data_enc"):
                return SendResult(success=True, status="SENT", http_status=200, raw=data)
            return SendResult(success=False, http_status=resp.status_code, raw=data)
        except Exception as e:
            return SendResult(success=False, error_detail=str(e))

    async def send_template(self, to: str, template_name: str, language: str, components: list | None = None) -> SendResult:
        return SendResult(success=False, error_detail="Rubika does not support templates")

    async def get_status(self, message_id: str) -> SendResult:
        return SendResult(success=True, external_id=message_id, status="SENT")