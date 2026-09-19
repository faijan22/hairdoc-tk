import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class PushProviderError(Exception):
    pass


class ExpoPushProvider:
    endpoint = "https://exp.host/--/api/v2/push/send"
    receipts_endpoint = "https://exp.host/--/api/v2/push/getReceipts"

    def _post(self, endpoint, payload):
        request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={
            "Accept": "application/json", "Content-Type": "application/json",
        })
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))["data"]
        except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as exc:
            raise PushProviderError("PROVIDER_UNAVAILABLE") from exc

    def send(self, token, title, body, data):
        if not settings.PUSH_NOTIFICATIONS_ENABLED:
            raise PushProviderError("PUSH_DISABLED")
        payload = {
            "to": token, "title": title, "body": body, "data": data,
            "sound": "default", "channelId": "care-updates", "priority": "high",
        }
        result = self._post(self.endpoint, payload)
        if result.get("status") != "ok":
            raise PushProviderError(result.get("details", {}).get("error") or result.get("message") or "REJECTED")
        return result.get("id", "")

    def receipts(self, ticket_ids):
        if not settings.PUSH_NOTIFICATIONS_ENABLED:
            raise PushProviderError("PUSH_DISABLED")
        result = self._post(self.receipts_endpoint, {"ids": ticket_ids})
        if not isinstance(result, dict):
            raise PushProviderError("INVALID_RECEIPT_RESPONSE")
        return result
