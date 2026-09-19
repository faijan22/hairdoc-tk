import base64
import hashlib
import hmac
import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .base import CheckoutSession, PaymentProviderConfigurationError


class SquarePaymentProvider:
    code = "SQUARE"

    def __init__(self):
        self.access_token = settings.SQUARE_ACCESS_TOKEN.strip()
        self.location_id = settings.SQUARE_LOCATION_ID.strip()
        self.environment = settings.SQUARE_ENVIRONMENT.strip().lower()
        self.base_url = (
            "https://connect.squareup.com"
            if self.environment == "production"
            else "https://connect.squareupsandbox.com"
        )

    def _ensure_checkout_configured(self):
        if not self.access_token or not self.location_id:
            raise PaymentProviderConfigurationError("Square checkout is not configured yet.")
        if self.environment not in {"sandbox", "production"}:
            raise PaymentProviderConfigurationError("Square environment must be sandbox or production.")

    def _request(self, method, path, payload):
        self._ensure_checkout_configured()
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method=method,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Square-Version": settings.SQUARE_API_VERSION,
            },
        )
        try:
            with urlopen(request, timeout=12) as response:  # noqa: S310 - fixed Square HTTPS hosts
                return json.loads(response.read() or b"{}")
        except HTTPError as exc:
            detail = "Square rejected the checkout request."
            try:
                errors = json.loads(exc.read()).get("errors") or []
                if errors and errors[0].get("detail"):
                    detail = str(errors[0]["detail"])
            except (json.JSONDecodeError, AttributeError, IndexError):
                pass
            raise PaymentProviderConfigurationError(detail) from exc
        except (URLError, TimeoutError) as exc:
            raise ConnectionError("Square checkout could not be reached.") from exc

    def create_checkout(self, *, order, attempt, return_base_url):
        item = order.items.get()
        expires_at = min(
            order.appointment.reservation_expires_at or timezone.now() + timedelta(minutes=30),
            timezone.now() + timedelta(minutes=30),
        )
        data = self._request("POST", "/v2/online-checkout/payment-links", {
            "idempotency_key": attempt.idempotency_key,
            "description": f"HairDoc TK appointment {order.public_id}",
            "payment_note": f"HairDoc TK order {order.public_id}",
            "order": {
                "location_id": self.location_id,
                "reference_id": str(order.public_id),
                "line_items": [{
                    "name": item.description[:255],
                    "quantity": str(item.quantity),
                    "base_price_money": {
                        "amount": _minor_units(item.unit_amount, order.currency),
                        "currency": order.currency,
                    },
                }],
            },
            "checkout_options": {
                "redirect_url": f"{return_base_url.rstrip('/')}/success/?order={order.public_id}",
                "ask_for_shipping_address": False,
                "allow_tipping": False,
            },
            "pre_populated_data": {"buyer_email": order.user.email},
        })
        link = data.get("payment_link") or {}
        if not link.get("id") or not link.get("order_id") or not link.get("url"):
            raise PaymentProviderConfigurationError("Square returned an incomplete checkout link.")
        return CheckoutSession(
            session_id=str(link["id"]),
            order_id=str(link["order_id"]),
            url=str(link["url"]),
            expires_at=expires_at,
        )

    def parse_webhook(self, payload, signature):
        key = settings.SQUARE_WEBHOOK_SIGNATURE_KEY.strip()
        notification_url = settings.SQUARE_WEBHOOK_NOTIFICATION_URL.strip()
        if not key or not notification_url:
            raise PaymentProviderConfigurationError("Square webhooks are not configured yet.")
        expected = base64.b64encode(
            hmac.new(
                key.encode("utf-8"),
                notification_url.encode("utf-8") + payload,
                hashlib.sha256,
            ).digest(),
        ).decode("ascii")
        if not signature or not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Square webhook signature.")
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid Square webhook payload.") from exc


def _minor_units(amount, currency):
    zero_decimal = {
        "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
    }
    multiplier = 1 if currency.upper() in zero_decimal else 100
    minor = amount * multiplier
    if minor != minor.to_integral_value():
        raise PaymentProviderConfigurationError("The service price cannot be represented in this currency's minor unit.")
    return int(minor)
