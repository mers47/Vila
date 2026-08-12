from app.connectors.base import MessagingConnector, SendResult
from app.connectors.http import HttpClient
from app.connectors.result import success_result, failure_result
from app.core.config import get_settings


class RubikaConnector(MessagingConnector):
    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    async def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
        token = self.settings.rubika_bot_token
        if not token:
            return SendResult(False, error_code="CONFIG", error_detail="Rubika token missing")
        url = f"https://botapi.rubika.ir/v3/{token}/sendMessage"
        response = await self.http.request("POST", url, json={"chat_id": recipient, "text": text})
        data = response.json() if response.content else {}
        nested = data.get("data") if isinstance(data, dict) else None
        result = data.get("result") if isinstance(data, dict) else None
        msg_id = (
            (nested or {}).get("message_id") if isinstance(nested, dict) else None
        ) or ((result or {}).get("message_id") if isinstance(result, dict) else None) or (
            data.get("message_id") if isinstance(data, dict) else None
        )
        explicit_error = data.get("error") if isinstance(data, dict) else None
        if response.is_success and not explicit_error:
            return success_result(response, str(msg_id) if msg_id else None)
        return failure_result(response)
