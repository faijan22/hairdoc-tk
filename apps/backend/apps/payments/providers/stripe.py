import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .base import CheckoutSession, PaymentProviderConfigurationError


class StripePaymentProvider:
    code = "STRIPE"

    def __init__(self):
        self.secret_key = settings.STRIPE_SECRET_KEY.strip()
        self.environment = settings.STRIPE_ENVIRONMENT.strip().lower()
        self.base_url = settings.STRIPE_API_BASE_URL.rstrip("/")

    def _ensure_checkout_configured(self):
        if self.environment not in {"test", "production"}:
            raise PaymentProviderConfigurationError("Stripe environment must be test or production.")
        if not self.secret_key:
            raise PaymentProviderConfigurationError("Stripe checkout is not configured yet.")
        expected = ("sk_test_", "rk_test_", "rkcs_test_") if self.environment == "test" else ("sk_live_", "rk_live_")
        if not self.secret_key.startswith(expected):
            required = "test" if self.environment == "test" else "live"
            raise PaymentProviderConfigurationError(f"Stripe {required}-mode credentials are required.")
        if not self.base_url.startswith("https://"):
            raise PaymentProviderConfigurationError("Stripe API URL must use HTTPS.")

    def _request(self, path, fields, *, idempotency_key):
        self._ensure_checkout_configured()
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Idempotency-Key": idempotency_key,
        }
        if settings.STRIPE_API_VERSION.strip():
            headers["Stripe-Version"] = settings.STRIPE_API_VERSION.strip()
        request = Request(
            f"{self.base_url}{path}",
            data=urlencode(fields).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urlopen(request, timeout=12) as response:  # noqa: S310 - configured HTTPS Stripe host
                return json.loads(response.read() or b"{}")
        except HTTPError as exc:
            detail = "Stripe rejected the checkout request."
            try:
                message = (json.loads(exc.read()).get("error") or {}).get("message")
                if message:
                    detail = str(message)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise PaymentProviderConfigurationError(detail) from exc
        except (URLError, TimeoutError) as exc:
            raise ConnectionError("Stripe checkout could not be reached.") from exc

    def retrieve_checkout(self, session_id):
        self._ensure_checkout_configured()
        if not session_id.startswith("cs_"):
            raise PaymentProviderConfigurationError("Stripe checkout identity is invalid.")
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        if settings.STRIPE_API_VERSION.strip():
            headers["Stripe-Version"] = settings.STRIPE_API_VERSION.strip()
        request = Request(
            f"{self.base_url}/v1/checkout/sessions/{quote(session_id, safe='')}",
            method="GET",
            headers=headers,
        )
        try:
            with urlopen(request, timeout=12) as response:  # noqa: S310 - configured HTTPS Stripe host
                return json.loads(response.read() or b"{}")
        except HTTPError as exc:
            detail = "Stripe could not verify this checkout session."
            try:
                message = (json.loads(exc.read()).get("error") or {}).get("message")
                if message:
                    detail = str(message)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise PaymentProviderConfigurationError(detail) from exc
        except (URLError, TimeoutError) as exc:
            raise ConnectionError("Stripe checkout could not be reached.") from exc

    def create_checkout(self, *, order, attempt, return_base_url):
        item = order.items.get()
        expires_at = timezone.now() + timedelta(minutes=31)
        base = return_base_url.rstrip("/")
        data = self._request(
            "/v1/checkout/sessions",
            [
                ("mode", "payment"),
                ("success_url", f"{base}/success/?order={order.public_id}&session_id={{CHECKOUT_SESSION_ID}}"),
                ("cancel_url", f"{base}/cancel/?order={order.public_id}"),
                ("client_reference_id", str(order.public_id)),
                ("customer_email", order.user.email),
                ("expires_at", str(int(expires_at.timestamp()))),
                ("metadata[hairdoc_order_id]", str(order.public_id)),
                ("payment_intent_data[capture_method]", "automatic"),
                ("payment_intent_data[metadata][hairdoc_order_id]", str(order.public_id)),
                ("line_items[0][quantity]", str(item.quantity)),
                ("line_items[0][price_data][currency]", order.currency.lower()),
                ("line_items[0][price_data][unit_amount]", str(_minor_units(item.unit_amount, order.currency))),
                ("line_items[0][price_data][product_data][name]", item.description[:255]),
            ],
            idempotency_key=attempt.idempotency_key,
        )
        if not data.get("id") or not data.get("url"):
            raise PaymentProviderConfigurationError("Stripe returned an incomplete checkout session.")
        provider_id = str(data["id"])
        return CheckoutSession(
            session_id=provider_id,
            order_id=provider_id,
            url=str(data["url"]),
            expires_at=timezone.datetime.fromtimestamp(
                int(data.get("expires_at") or expires_at.timestamp()), tz=timezone.get_current_timezone(),
            ),
        )

    def parse_webhook(self, payload, signature):
        secret = settings.STRIPE_WEBHOOK_SECRET.strip()
        if not secret:
            raise PaymentProviderConfigurationError("Stripe webhooks are not configured yet.")
        parts = {}
        for item in signature.split(","):
            key, separator, value = item.partition("=")
            if separator:
                parts.setdefault(key.strip(), []).append(value.strip())
        try:
            timestamp = int(parts["t"][0])
        except (KeyError, ValueError, IndexError) as exc:
            raise ValueError("Invalid Stripe webhook signature.") from exc
        if abs(int(time.time()) - timestamp) > settings.STRIPE_WEBHOOK_TOLERANCE_SECONDS:
            raise ValueError("Expired Stripe webhook signature.")
        expected = hmac.new(
            secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + payload, hashlib.sha256,
        ).hexdigest()
        if not any(hmac.compare_digest(expected, candidate) for candidate in parts.get("v1", [])):
            raise ValueError("Invalid Stripe webhook signature.")
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid Stripe webhook payload.") from exc
        if event.get("livemode") is not (self.environment == "production"):
            raise ValueError("Stripe webhook mode does not match the configured environment.")
        return event


def _minor_units(amount, currency):
    zero_decimal = {
        "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
    }
    multiplier = 1 if currency.upper() in zero_decimal else 100
    minor = amount * multiplier
    if minor != minor.to_integral_value():
        raise PaymentProviderConfigurationError("The service price cannot be represented in this currency's minor unit.")
    return int(minor)
