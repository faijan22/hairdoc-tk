import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings

from .base import JoinGrant, VideoProviderError


class DailyVideoProvider:
    code = "DAILY"

    def __init__(self):
        self.api_key = settings.DAILY_API_KEY.strip()
        self.api_base_url = settings.DAILY_API_BASE_URL.rstrip("/")
        self.domain = settings.DAILY_DOMAIN.rstrip("/")

    @property
    def is_configured(self):
        return bool(self.api_key and self.domain and urlparse(self.domain).scheme == "https")

    def _request(self, method, path, payload=None, *, allow_not_found=False):
        if not self.is_configured:
            raise VideoProviderError("Secure video is not configured yet.")
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            f"{self.api_base_url}{path}", data=body, method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed configured HTTPS vendor base
                return json.loads(response.read() or b"{}")
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            detail = ""
            try:
                detail = json.loads(exc.read()).get("info", "")
            except (json.JSONDecodeError, AttributeError):
                pass
            raise VideoProviderError(detail or "The video provider rejected the request.") from exc
        except (URLError, TimeoutError) as exc:
            raise VideoProviderError("The video provider could not be reached.") from exc

    def create_room(self, *, room_id, available_from, expires_at):
        existing = self._request("GET", f"/rooms/{quote(room_id)}", allow_not_found=True)
        if existing:
            return
        self._request("POST", "/rooms", {
            "name": room_id,
            "privacy": "private",
            "properties": {
                "nbf": int(available_from.timestamp()),
                "exp": int(expires_at.timestamp()),
                "max_participants": 2,
                "enable_prejoin_ui": True,
                "enable_people_ui": False,
                "enable_chat": False,
                "enable_advanced_chat": False,
                "enable_screenshare": False,
                "enforce_unique_user_ids": True,
                "start_video_off": True,
                "start_audio_off": True,
            },
        })

    def issue_join_grant(
        self, *, room_id, user_id, user_name, is_owner, available_from, expires_at,
    ):
        data = self._request("POST", "/meeting-tokens", {"properties": {
            "room_name": room_id,
            "user_id": user_id[:36],
            "user_name": user_name[:80],
            "is_owner": is_owner,
            "nbf": int(available_from.timestamp()),
            "exp": int(expires_at.timestamp()),
            "eject_at_token_exp": True,
            "enable_screenshare": False,
            "enable_recording_ui": False,
            "enable_prejoin_ui": True,
            "start_video_off": True,
            "start_audio_off": True,
            "close_tab_on_exit": True,
        }})
        token = data.get("token")
        if not token:
            raise VideoProviderError("The video provider returned no join token.")
        return JoinGrant(
            url=f"{self.domain}/{quote(room_id)}?{urlencode({'t': token})}",
            expires_at=expires_at,
        )

    def close_room(self, *, room_id):
        self._request("DELETE", f"/rooms/{quote(room_id)}", allow_not_found=True)
