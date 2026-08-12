from app.connectors.base import MessagingConnector, SendResult
from app.connectors.http import HttpClient
from app.connectors.result import success_result, failure_result
from app.core.config import get_settings


class WhatsAppConnector(MessagingConnector):
    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    def _config(self, endpoint: str = "messages"):
        s = self.settings
        if not s.whatsapp_access_token or not s.whatsapp_phone_number_id:
            return None, None
        url = f"https://graph.facebook.com/{s.whatsapp_graph_version}/{s.whatsapp_phone_number_id}/{endpoint}"
        headers = {"Authorization": f"Bearer {s.whatsapp_access_token}", "Content-Type": "application/json"}
        return url, headers

    async def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
        url, headers = self._config()
        if not url:
            return SendResult(False, error_code="CONFIG", error_detail="WhatsApp credentials missing")
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": text}}
        return await self._send(url, headers, payload)

    @staticmethod
    def _template_payload(recipient: str, name: str, language: str, components: list | None) -> dict:
        template = {"name": name, "language": {"code": language}}
        if components:
            template["components"] = components
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": template,
        }

    async def send_template(self, recipient: str, *, name: str, language: str = "fa", components: list | None = None) -> SendResult:
        url, headers = self._config("messages")
        if not url:
            return SendResult(False, error_code="CONFIG", error_detail="WhatsApp credentials missing")
        return await self._send(url, headers, self._template_payload(recipient, name, language, components))

    async def send_marketing_template(
        self, recipient: str, *, name: str, language: str = "fa", components: list | None = None
    ) -> SendResult:
        url, headers = self._config("marketing_messages")
        if not url:
            return SendResult(False, error_code="CONFIG", error_detail="WhatsApp credentials missing")
        return await self._send(url, headers, self._template_payload(recipient, name, language, components))

    async def _send(self, url: str, headers: dict, payload: dict) -> SendResult:
        response = await self.http.request("POST", url, headers=headers, json=payload)
        if response.is_success:
            data = response.json()
            msg_id = (data.get("messages") or [{}])[0].get("id")
            return success_result(response, msg_id)
        return failure_result(response)
