import httpx

from app.connectors.base import BaseConnector
from app.connectors.http import HttpClient
from app.connectors.result import SendResult
from app.core.config import get_settings


class EitaaConnector(BaseConnector):
    def __init__(self):
        s = get_settings()
        self.app_token = s.eitaa_app_token
        self._base = f"https://eitaayar.ir/api/{self.app_token}" if self.app_token else ""

    async def send_text(self, to: str, text: str) -> SendResult:
        if not self.app_token:
            return SendResult(success=False, error_code="NOT_CONFIGURED")
        client = await HttpClient.get_client()
        try:
            resp = await client.post(f"{self._base}/sendMessage", data={"chat_id": to, "text": text})
            data = resp.json()
            if data.get("ok"):
                return SendResult(success=True, external_id=str(data["result"]["message_id"]), status="SENT", http_status=200, raw=data)
            return SendResult(success=False, http_status=resp.status_code, error_code=str(data.get("error_code", "")), raw=data)
        except Exception as e:
            return SendResult(success=False, error_detail=str(e))

    async def send_template(self, to: str, template_name: str, language: str, components: list | None = None) -> SendResult:
        return SendResult(success=False, error_detail="Eitaa does not support templates")

    async def get_status(self, message_id: str) -> SendResult:
        return SendResult(success=True, external_id=message_id, status="SENT")