import httpx

from app.connectors.base import BaseConnector
from app.connectors.http import HttpClient
from app.connectors.result import SendResult
from app.core.config import get_settings


class TelegramConnector(BaseConnector):
    def __init__(self):
        s = get_settings()
        self.bot_token = s.telegram_bot_token
        self._base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    async def send_text(self, to: str, text: str) -> SendResult:
        if not self.bot_token:
            return SendResult(success=False, error_code="NOT_CONFIGURED")
        client = await HttpClient.get_client()
        try:
            resp = await client.post(f"{self._base}/sendMessage", json={"chat_id": to, "text": text})
            data = resp.json()
            if data.get("ok"):
                return SendResult(success=True, external_id=str(data["result"]["message_id"]), status="SENT", http_status=200, raw=data)
            return SendResult(success=False, http_status=resp.status_code, error_code=str(data.get("error_code", "")), error_detail=data.get("description"), raw=data)
        except Exception as e:
            return SendResult(success=False, error_detail=str(e))

    async def send_template(self, to: str, template_name: str, language: str, components: list | None = None) -> SendResult:
        return SendResult(success=False, error_detail="Telegram does not support templates — use send_text")

    async def get_status(self, message_id: str) -> SendResult:
        return SendResult(success=True, external_id=message_id, status="UNKNOWN", raw={"note": "Telegram does not provide delivery status"})