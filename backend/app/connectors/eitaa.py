from app.connectors.base import MessagingConnector, SendResult
from app.connectors.http import HttpClient
from app.connectors.result import success_result, failure_result
from app.core.config import get_settings


class EitaaConnector(MessagingConnector):
    endpoint = "https://eitaayar.ir/api/app/sendMessage"

    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    async def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
        token = self.settings.eitaa_app_token
        if not token:
            return SendResult(False, error_code="CONFIG", error_detail="Eitaa token missing")
        response = await self.http.request("POST", self.endpoint, json={"token": token, "chat_id": recipient, "text": text})
        data = response.json()
        if response.is_success and data.get("ok") is True:
            return success_result(response, str(data.get("result", "success")))
        return failure_result(response)
