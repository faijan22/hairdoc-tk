from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse

from .base import *  # noqa: F403

# Never permit the development-only photo-consent bypass in production.
PHOTO_CONSENT_REQUIRED = True

missing = []
if not SECRET_KEY:  # noqa: F405
    missing.append("DJANGO_SECRET_KEY")
if not ALLOWED_HOSTS:  # noqa: F405
    missing.append("DJANGO_ALLOWED_HOSTS")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":  # noqa: F405
    missing.append("DATABASE_URL (PostgreSQL required)")
if SQUARE_ENVIRONMENT != "production":  # noqa: F405
    missing.append("SQUARE_ENVIRONMENT=production")
if not SQUARE_ACCESS_TOKEN:  # noqa: F405
    missing.append("SQUARE_ACCESS_TOKEN")
if not SQUARE_LOCATION_ID:  # noqa: F405
    missing.append("SQUARE_LOCATION_ID")
if not SQUARE_WEBHOOK_SIGNATURE_KEY:  # noqa: F405
    missing.append("SQUARE_WEBHOOK_SIGNATURE_KEY")
if urlparse(SQUARE_WEBHOOK_NOTIFICATION_URL).scheme != "https":  # noqa: F405
    missing.append("SQUARE_WEBHOOK_NOTIFICATION_URL (HTTPS required)")
if urlparse(PAYMENT_RETURN_BASE_URL).scheme != "https":  # noqa: F405
    missing.append("PAYMENT_RETURN_BASE_URL (HTTPS required)")
if VIDEO_PROVIDER_BACKEND.endswith(".DailyVideoProvider"):  # noqa: F405
    if not DAILY_API_KEY:  # noqa: F405
        missing.append("DAILY_API_KEY")
    if urlparse(DAILY_DOMAIN).scheme != "https":  # noqa: F405
        missing.append("DAILY_DOMAIN (HTTPS required)")
if CHANNEL_LAYERS["default"]["BACKEND"] != "channels_redis.core.RedisChannelLayer":  # noqa: F405
    missing.append("USE_REDIS_CHANNEL_LAYER=true")
if missing:
    raise ImproperlyConfigured(f"Missing production configuration: {', '.join(missing)}")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
