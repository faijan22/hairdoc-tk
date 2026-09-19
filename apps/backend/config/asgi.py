import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django_asgi_app = get_asgi_application()

from apps.messaging.routing import websocket_urlpatterns  # noqa: E402


class NativeOrAllowedHostOriginValidator:
    """Browsers must have an allowed Origin; native clients authenticate by one-use ticket."""

    def __init__(self, app):
        self.app = app
        self.browser_validator = AllowedHostsOriginValidator(app)

    async def __call__(self, scope, receive, send):
        if any(name.lower() == b"origin" for name, _ in scope.get("headers", [])):
            return await self.browser_validator(scope, receive, send)
        return await self.app(scope, receive, send)


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": NativeOrAllowedHostOriginValidator(URLRouter(websocket_urlpatterns)),
})
