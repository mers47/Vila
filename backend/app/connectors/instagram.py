from app.connectors.base import MessagingConnector, SendResult
from app.connectors.http import HttpClient
from app.connectors.result import success_result, failure_result
from app.core.config import get_settings


class InstagramConnector(MessagingConnector):
    def __init__(self):
        self.settings = get_settings()
        self.http = HttpClient()

    async def send_text(self, recipient: str, text: str, **kwargs) -> SendResult:
        s = self.settings
        if not s.instagram_access_token or not s.instagram_business_account_id:
            return SendResult(False, error_code="CONFIG", error_detail="Instagram credentials missing")
        url = f"https://graph.instagram.com/{s.instagram_graph_version}/{s.instagram_business_account_id}/messages"
        payload = {"recipient": {"id": recipient}, "message": {"text": text}}
        response = await self.http.request("POST", url, params={"access_token": s.instagram_access_token}, json=payload)
        if response.is_success:
            data = response.json()
            return success_result(response, data.get("message_id"))
        return failure_result(response)
