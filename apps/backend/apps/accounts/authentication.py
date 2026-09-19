import jwt
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import DeviceSession
from .services import decode_access_token


class AccessTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if len(parts) != 2 or parts[0].decode("ascii", errors="ignore").lower() != self.keyword.lower():
            raise AuthenticationFailed("Authentication credentials were invalid.", code="invalid_token")

        try:
            payload = decode_access_token(parts[1].decode("ascii"))
        except (UnicodeDecodeError, jwt.PyJWTError):
            raise AuthenticationFailed("Authentication credentials were invalid.", code="invalid_token") from None

        if payload.get("type") != "access":
            raise AuthenticationFailed("Authentication credentials were invalid.", code="invalid_token")

        session = (
            DeviceSession.objects.select_related("user")
            .filter(public_id=payload["sid"], user__public_id=payload["sub"])
            .first()
        )
        if not session or not session.is_active or not session.user.is_active:
            raise AuthenticationFailed("Authentication credentials were invalid.", code="invalid_token")
        return session.user, session


    def authenticate_header(self, request) -> str:
        return self.keyword
