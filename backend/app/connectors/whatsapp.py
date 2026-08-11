import httpx

from app.connectors.base import BaseConnector
from app.connectors.http import HttpClient
from app.connectors.result import SendResult
from app.core.config import get_settings


class WhatsAppConnector(BaseConnector):
    def __init__(self):
        s = get_settings()
        self.access_token = s.whatsapp_access_token
        self.phone_number_id = s.whatsapp_phone_number_id
        self.graph_version = s.whatsapp_graph_version
        self._base = f"https://graph.facebook.com/{self.graph_version}/{self.phone_number_id}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    async def send_text(self, to: str, text: str) -> SendResult:
        if not self.access_token:
            return SendResult(success=False, error_code="NOT_CONFIGURED", error_detail="WhatsApp not configured")
        client = await HttpClient.get_client()
        try:
            resp = await client.post(
                f"{self._base}/messages",
                json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
                headers=self._headers(),
            )
            data = resp.json()
            if resp.status_code == 200:
                return SendResult(success=True, external_id=data.get("messages", [{}])[0].get("id"), status="SENT", http_status=200, raw=data)
            return SendResult(success=False, http_status=resp.status_code, error_code=data.get("error", {}).get("code"), error_detail=str(data.get("error", {}).get("message", "")), raw=data)
        except Exception as e:
            return SendResult(success=False, error_detail=str(e))

    async def send_template(self, to: str, template_name: str, language: str, components: list | None = None) -> SendResult:
        if not self.access_token:
            return SendResult(success=False, error_code="NOT_CONFIGURED")
        client = await HttpClient.get_client()
        try:
            resp = await client.post(
                f"{self._base}/messages",
                json={"messaging_product": "whatsapp", "to": to, "type": "template", "template": {"name": template_name, "language": {"code": language}, "components": components or []}},
                headers=self._headers(),
            )
            data = resp.json()
            if resp.status_code == 200:
                return SendResult(success=True, external_id=data.get("messages", [{}])[0].get("id"), status="SENT", http_status=200, raw=data)
            return SendResult(success=False, http_status=resp.status_code, error_code=data.get("error", {}).get("code"), raw=data)
        except Exception as e:
            return SendResult(success=False, error_detail=str(e))

    async def get_status(self, message_id: str) -> SendResult:
        client = await HttpClient.get_client()
        try:
            resp = await client.get(f"{self._base}/messages/{message_id}", headers=self._headers())
            data = resp.json()
            return SendResult(success=True, external_id=message_id, status=data.get("status", "UNKNOWN"), http_status=resp.status_code, raw=data)
        except Exception as e:
            return SendResult(success=False, error_detail=str(e))