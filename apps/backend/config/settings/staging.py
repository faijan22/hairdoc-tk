from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
PHOTO_CONSENT_REQUIRED = True

missing = []
if not SECRET_KEY or len(SECRET_KEY) < 50:  # noqa: F405
    missing.append("DJANGO_SECRET_KEY (at least 50 characters)")
if not ALLOWED_HOSTS:  # noqa: F405
    missing.append("DJANGO_ALLOWED_HOSTS")
if not CSRF_TRUSTED_ORIGINS:  # noqa: F405
    missing.append("CSRF_TRUSTED_ORIGINS")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":  # noqa: F405
    missing.append("DATABASE_URL (PostgreSQL required)")
if STRIPE_ENVIRONMENT != "test":  # noqa: F405
    missing.append("STRIPE_ENVIRONMENT=test")
if not STRIPE_SECRET_KEY.startswith(("sk_test_", "rk_test_")):  # noqa: F405
    missing.append("STRIPE_SECRET_KEY (test key required)")
if not STRIPE_WEBHOOK_SECRET.startswith("whsec_"):  # noqa: F405
    missing.append("STRIPE_WEBHOOK_SECRET")
if urlparse(PAYMENT_RETURN_BASE_URL).scheme != "https":  # noqa: F405
    missing.append("PAYMENT_RETURN_BASE_URL (HTTPS required)")
if CHANNEL_LAYERS["default"]["BACKEND"] != "channels_redis.core.RedisChannelLayer":  # noqa: F405
    missing.append("USE_REDIS_CHANNEL_LAYER=true")
if EMAIL_NOTIFICATIONS_ENABLED and EMAIL_BACKEND.endswith("console.EmailBackend"):  # noqa: F405
    missing.append("EMAIL_BACKEND (real provider required when email is enabled)")
if missing:
    raise ImproperlyConfigured(f"Missing staging configuration: {', '.join(missing)}")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 86400
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

