from redis import Redis
from redis.exceptions import RedisError

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "unsafe-development-key-change-before-deployment"  # noqa: F405
# Development is intentionally reachable from physical devices on the active LAN.
# Production keeps the explicit host/origin allowlists defined in base settings.
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# Local devices may exercise the real private upload pipeline before owner-approved
# legal copy exists. Base/production settings remain fail-closed by default.
PHOTO_CONSENT_REQUIRED = False

# Keep local chat genuinely realtime even when a stale WSL/Docker port accepts
# TCP connections without answering Redis commands. Production remains Redis-
# only; development safely falls back to the single-process Channels layer and
# reports the reason at startup instead of dropping sockets after they connect.
if CHANNEL_LAYERS["default"]["BACKEND"] == "channels_redis.core.RedisChannelLayer":  # noqa: F405
    try:
        redis_client = Redis.from_url(  # noqa: F405
            REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5  # noqa: F405
        )
        redis_client.ping()
        redis_client.close()
    except (RedisError, OSError):
        CHANNEL_LAYERS = {  # noqa: F405
            "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
        }
        print(
            "WARNING: Redis is unavailable; local realtime messaging is using "
            "the single-process in-memory channel layer. Start Redis and restart "
            "Django to exercise the production-like Redis transport."
        )
