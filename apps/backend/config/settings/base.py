from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DJANGO_ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    USE_REDIS_CHANNEL_LAYER=(bool, False),
    AUTH_ACCESS_TOKEN_MINUTES=(int, 15),
    AUTH_REFRESH_TOKEN_DAYS=(int, 30),
    AUTH_ACTION_TOKEN_MINUTES=(int, 30),
    VIDEO_JOIN_EARLY_MINUTES=(int, 10),
    VIDEO_JOIN_LATE_MINUTES=(int, 15),
    PUSH_NOTIFICATIONS_ENABLED=(bool, False),
    EMAIL_NOTIFICATIONS_ENABLED=(bool, False),
    PHOTO_CONSENT_REQUIRED=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = False
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "channels",
    "apps.core",
    "apps.accounts",
    "apps.content",
    "apps.private_media",
    "apps.consultations",
    "apps.payments",
    "apps.messaging",
    "apps.notifications",
    "apps.video",
    "apps.coaching",
    "apps.progress",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = 60

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / ".media"))
PRIVATE_MEDIA_ROOT = env("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / ".private-media"))
PRIVATE_FILE_STORAGE_BACKEND = env(
    "PRIVATE_FILE_STORAGE_BACKEND",
    default="apps.private_media.storage.LocalPrivateStorage",
)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.authentication.AccessTokenAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "5/hour",
        "auth_login": "10/minute",
        "auth_token": "20/minute",
        "auth_recovery": "5/hour",
        "message_send": "30/minute",
        "realtime_ticket": "30/minute",
        "account_delete": "5/hour",
        "video_join": "10/minute",
    },
}

AUTH_ACCESS_TOKEN_MINUTES = env("AUTH_ACCESS_TOKEN_MINUTES")
AUTH_REFRESH_TOKEN_DAYS = env("AUTH_REFRESH_TOKEN_DAYS")
AUTH_ACTION_TOKEN_MINUTES = env("AUTH_ACTION_TOKEN_MINUTES")
AUTH_JWT_ISSUER = env("AUTH_JWT_ISSUER", default="hairdoc-tk-api")
AUTH_JWT_AUDIENCE = env("AUTH_JWT_AUDIENCE", default="hairdoc-tk-app")
AUTH_APP_URL = env("AUTH_APP_URL", default="hairdoctk://")
AUTH_REFRESH_COOKIE_NAME = "hairdoc_refresh"
AUTH_REFRESH_COOKIE_PATH = "/api/v1/auth/"

PAYMENT_PROVIDER_BACKEND = env(
    "PAYMENT_PROVIDER_BACKEND",
    default="apps.payments.providers.square.SquarePaymentProvider",
)
SQUARE_ENVIRONMENT = env("SQUARE_ENVIRONMENT", default="sandbox")
SQUARE_API_VERSION = env("SQUARE_API_VERSION", default="2026-08-19")
SQUARE_ACCESS_TOKEN = env("SQUARE_ACCESS_TOKEN", default="")
SQUARE_LOCATION_ID = env("SQUARE_LOCATION_ID", default="")
SQUARE_WEBHOOK_SIGNATURE_KEY = env("SQUARE_WEBHOOK_SIGNATURE_KEY", default="")
SQUARE_WEBHOOK_NOTIFICATION_URL = env("SQUARE_WEBHOOK_NOTIFICATION_URL", default="")
PAYMENT_RETURN_BASE_URL = env(
    "PAYMENT_RETURN_BASE_URL",
    default="http://127.0.0.1:8000/api/v1/payments/return",
)

VIDEO_PROVIDER_BACKEND = env(
    "VIDEO_PROVIDER_BACKEND",
    default="apps.video.providers.disabled.DisabledVideoProvider",
)
VIDEO_JOIN_EARLY_MINUTES = env("VIDEO_JOIN_EARLY_MINUTES")
VIDEO_JOIN_LATE_MINUTES = env("VIDEO_JOIN_LATE_MINUTES")
DAILY_API_KEY = env("DAILY_API_KEY", default="")
DAILY_API_BASE_URL = env("DAILY_API_BASE_URL", default="https://api.daily.co/v1")
DAILY_DOMAIN = env("DAILY_DOMAIN", default="")
PUSH_NOTIFICATIONS_ENABLED = env("PUSH_NOTIFICATIONS_ENABLED")
EMAIL_NOTIFICATIONS_ENABLED = env("EMAIL_NOTIFICATIONS_ENABLED")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="HairDoc TK <noreply@hairdoctk.invalid>")
PHOTO_CONSENT_REQUIRED = env("PHOTO_CONSENT_REQUIRED")

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, "x-hairdoc-client")

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
if env("USE_REDIS_CHANNEL_LAYER"):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            # channels-redis blocks for five seconds while waiting for work.
            # redis-py's current five-second default socket timeout would race
            # that normal wait and tear down otherwise healthy WebSockets.
            "CONFIG": {
                "hosts": [
                    {
                        "address": REDIS_URL,
                        "socket_connect_timeout": 2,
                        "socket_timeout": 10,
                    }
                ]
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "hairdoc-appointment-reminders": {
        "task": "apps.notifications.tasks.create_due_appointment_reminders",
        "schedule": 300.0,
    },
    "hairdoc-push-receipts": {
        "task": "apps.notifications.tasks.reconcile_push_receipts",
        "schedule": 900.0,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
