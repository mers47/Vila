from app.connectors.base import MessagingConnector, SendResult
from app.connectors.http import HttpClient
from app.connectors.result import success_result, failure_result
from app.core.config import get_settings


class TelegramConnector(MessagingConnector):
    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    async def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
        token = self.settings.telegram_bot_token
        if not token:
            return SendResult(False, error_code="CONFIG", error_detail="Telegram token missing")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = await self.http.request("POST", url, json={"chat_id": recipient, "text": text})
        data = response.json()
        if response.is_success and data.get("ok"):
            return success_result(response, str(data["result"]["message_id"]))
        return failure_result(response)
