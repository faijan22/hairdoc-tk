import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django_asgi_app = get_asgi_application()

from apps.messaging.routing import websocket_urlpatterns  # noqa: E402


class NativeOrAllowedOriginValidator:
    """Validate browser frontend origins while native clients use one-use tickets."""

    def __init__(self, app):
        self.app = app
        allowed = ["*"] if settings.CORS_ALLOW_ALL_ORIGINS else list({
            *settings.CORS_ALLOWED_ORIGINS,
            *settings.CSRF_TRUSTED_ORIGINS,
        })
        self.browser_validator = OriginValidator(app, allowed)

    async def __call__(self, scope, receive, send):
        if any(name.lower() == b"origin" for name, _ in scope.get("headers", [])):
            return await self.browser_validator(scope, receive, send)
        return await self.app(scope, receive, send)


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": NativeOrAllowedOriginValidator(URLRouter(websocket_urlpatterns)),
})
