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
if STRIPE_ENVIRONMENT != "production":  # noqa: F405
    missing.append("STRIPE_ENVIRONMENT=production")
if not STRIPE_SECRET_KEY.startswith(("sk_live_", "rk_live_")):  # noqa: F405
    missing.append("STRIPE_SECRET_KEY (live key required)")
if not STRIPE_WEBHOOK_SECRET.startswith("whsec_"):  # noqa: F405
    missing.append("STRIPE_WEBHOOK_SECRET")
if urlparse(PAYMENT_RETURN_BASE_URL).scheme != "https":  # noqa: F405
    missing.append("PAYMENT_RETURN_BASE_URL (HTTPS required)")
if VIDEO_PROVIDER_BACKEND.endswith(".DailyVideoProvider"):  # noqa: F405
    if not DAILY_API_KEY:  # noqa: F405
        missing.append("DAILY_API_KEY")
    if urlparse(DAILY_DOMAIN).scheme != "https":  # noqa: F405
        missing.append("DAILY_DOMAIN (HTTPS required)")
if CHANNEL_LAYERS["default"]["BACKEND"] != "channels_redis.core.RedisChannelLayer":  # noqa: F405
    missing.append("USE_REDIS_CHANNEL_LAYER=true")
if EMAIL_BACKEND.endswith("console.EmailBackend"):  # noqa: F405
    missing.append("EMAIL_BACKEND (real provider required for account email)")
if EMAIL_BACKEND.endswith("ElasticEmailBackend") and not ELASTIC_EMAIL_API_KEY:  # noqa: F405
    missing.append("ELASTIC_EMAIL_API_KEY")
if missing:
    raise ImproperlyConfigured(f"Missing production configuration: {', '.join(missing)}")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
